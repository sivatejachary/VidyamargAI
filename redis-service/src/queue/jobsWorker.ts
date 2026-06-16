import { Queue, Worker, Job } from "bullmq";
import redisConnectionManager from "../config/redis";
import webSocketSyncService from "../services/websocket";
import cacheInvalidationService from "../services/invalidation";
import { CacheKeyRegistry } from "../config/versions";
import pino from "pino";

const logger = pino({
  name: "jobs-refresh-worker",
  level: process.env.LOG_LEVEL || "info",
});

export interface JobsRefreshJobData {
  userId: string | number;
  candidateId: number;
}

// Reuse the writable Redis client connection for BullMQ
const connection = redisConnectionManager.getWritableClient() as any;

/**
 * Define the BullMQ queue for jobs refresh tasks
 */
export const jobsRefreshQueue = new Queue<JobsRefreshJobData>("jobs-refresh", {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: "exponential",
      delay: 5000, // 5s backoff
    },
    removeOnComplete: true,
    removeOnFail: 1000, // Keep last 1000 failures in history
  },
});

/**
 * BullMQ Worker processing background jobs revalidation (SWR trigger)
 */
export const jobsWorker = new Worker<JobsRefreshJobData>(
  "jobs-refresh",
  async (job: Job<JobsRefreshJobData>) => {
    const { userId, candidateId } = job.data;
    logger.info({ userId, jobId: job.id }, "Starting background jobs matching and revalidation");

    try {
      // 1. Fetch current cached jobs to calculate delta
      const cacheKey = CacheKeyRegistry.getKey("jobs", "matched", userId);
      const cachedEnvelope = await cacheInvalidationService.get<any[]>(
        "jobs",
        "matched",
        userId,
        async () => [] // return empty if missing
      );
      
      const existingJobIds = new Set(cachedEnvelope.map((j) => j.id));

      // 2. Fetch fresh matched jobs (Mocking DB queries + AI matching rules)
      const freshJobs = await fetchMockMatchedJobsFromDB(userId, candidateId);

      // 3. Diff old vs new listings
      const newJobs = freshJobs.filter((job) => !existingJobIds.has(job.id));
      const deltaCount = newJobs.length;

      logger.info({ userId, totalMatches: freshJobs.length, deltaCount }, "Jobs matching completed");

      // 4. Update the Redis cache with fresh results
      const ttlConfig = CacheKeyRegistry.getTTL("jobs", "matched");
      const version = 1;
      await cacheInvalidationService.set(cacheKey, freshJobs, ttlConfig, version);

      // 5. If new jobs are found, broadcast alert via WebSocket room
      if (deltaCount > 0) {
        logger.info({ userId, deltaCount }, "Broadcasting new jobs matching notification");
        const userRoom = `user:${userId}`;
        
        await webSocketSyncService.publishToPubSub(
          userRoom,
          "jobs:sync",
          {
            delta: deltaCount,
            total: freshJobs.length,
            message: `${deltaCount} new jobs matched for your profile!`,
            newJobs: newJobs.map((j) => ({ id: j.id, title: j.title, company: j.company })),
          }
        );
      }
    } catch (err: any) {
      logger.error({ userId, error: err.message }, "Jobs refresh worker execution failed");
      throw err; // triggers BullMQ automatic retry
    }
  },
  {
    connection,
    concurrency: 5, // Process up to 5 users concurrently per node
  }
);

/**
 * Mock database retriever for candidate matched jobs.
 * Filters listings matching candidate characteristics.
 */
async function fetchMockMatchedJobsFromDB(userId: string | number, candidateId: number): Promise<any[]> {
  // Simulate DB latency
  await new Promise((resolve) => setTimeout(resolve, 500));

  // In production, this runs a SQL query:
  // SELECT j.* FROM jobs j JOIN job_matches jm ON j.id = jm.job_id WHERE jm.candidate_id = :candidateId AND jm.match_score >= 80
  
  // Return mock listings matching user skills
  const mockAllJobs = [
    { id: 101, title: "Fastify Engineer", company: "Meta", score: 95, location: "Remote" },
    { id: 102, title: "Redis Platform Developer", company: "Stripe", score: 92, location: "San Francisco, CA" },
    { id: 103, title: "TypeScript Architect", company: "Netflix", score: 89, location: "Los Gatos, CA" },
    { id: 104, title: "Node.js Platform Lead", company: "Google", score: 94, location: "New York, NY" },
    { id: 105, title: "Senior Backend Engineer", company: "Amazon", score: 85, location: "Seattle, WA" },
  ];

  // Randomly add a new job to simulate background crawls discovering new entries
  const numJobs = Math.floor(Math.random() * 2) === 1 ? 5 : 4;
  return mockAllJobs.slice(0, numJobs);
}

jobsWorker.on("completed", (job) => {
  logger.info({ jobId: job.id, userId: job.data.userId }, "Jobs refresh task completed successfully");
});

jobsWorker.on("failed", (job, err) => {
  logger.error({ jobId: job?.id, error: err.message }, "Jobs refresh task failed in worker");
});
