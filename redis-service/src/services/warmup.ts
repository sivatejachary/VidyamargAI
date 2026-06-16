import { Cluster } from "ioredis";
import Redis from "ioredis";
import redisConnectionManager from "../config/redis";
import webSocketSyncService from "./websocket";
import { CacheKeyRegistry, CacheModule, CACHE_TTLS } from "../config/versions";
import cacheInvalidationService from "./invalidation";
import pino from "pino";

const logger = pino({
  name: "login-warmup-service",
  level: process.env.LOG_LEVEL || "info",
});

export interface WarmupTiers {
  tier1: CacheModule[];
  tier2: CacheModule[];
  tier3: CacheModule[];
}

export class LoginWarmupService {
  private redis: Redis | Cluster;

  constructor() {
    this.redis = redisConnectionManager.getWritableClient();
  }

  /**
   * Tracks a user's page visit history (maintains last 5 pages in a Redis List).
   */
  public async trackPageVisit(userId: string | number, page: string): Promise<void> {
    const key = `user:navigation:${userId}`;
    try {
      // Push page to list and trim to keep only the 5 most recent pages
      const pipeline = this.redis.pipeline();
      pipeline.lpush(key, page);
      pipeline.ltrim(key, 0, 4);
      await pipeline.exec();
      logger.info({ userId, page }, "Tracked page visit in navigation history");
    } catch (err: any) {
      logger.error({ userId, page, error: err.message }, "Failed to track page visit");
    }
  }

  /**
   * Identifies promoted modules based on the candidate's last 5 page visits.
   */
  public async getPromotedModules(userId: string | number): Promise<CacheModule[]> {
    const key = `user:navigation:${userId}`;
    try {
      const history = await this.redis.lrange(key, 0, -1);
      if (!history || history.length === 0) return [];

      // Map pages/routes to modules
      const moduleFrequency: Record<string, number> = {};
      history.forEach((page) => {
        let mod: CacheModule | null = null;
        if (page.includes("/candidate/resume")) mod = "resume";
        else if (page.includes("/candidate/jobs")) mod = "jobs";
        else if (page.includes("/candidate/chat")) mod = "ai_chat";
        else if (page.includes("/candidate/messages")) mod = "messages";
        else if (page.includes("/candidate/notifications")) mod = "notifications";
        else if (page.includes("/candidate/skill-lab") || page.includes("/candidate/assessments")) mod = "skill_lab";
        else if (page.includes("/candidate/hackathons")) mod = "hackathons";
        
        if (mod) {
          moduleFrequency[mod] = (moduleFrequency[mod] || 0) + 1;
        }
      });

      // Sort modules by frequency descending
      return Object.keys(moduleFrequency)
        .sort((a, b) => moduleFrequency[b] - moduleFrequency[a]) as CacheModule[];
    } catch (err: any) {
      logger.error({ userId, error: err.message }, "Error reading page navigation history");
      return [];
    }
  }

  /**
   * Triggers the 3-tier background cache warmup pipeline asynchronously after login.
   */
  public async triggerWarmup(userId: string | number): Promise<void> {
    logger.info({ userId }, "Triggering login cache warmup process");

    // Execute warmup process asynchronously
    this.executeWarmupPipeline(userId).catch((err) => {
      logger.error({ userId, error: err.message }, "Login cache warmup execution failed");
    });
  }

  /**
   * Asynchronous executor for warming tiers based on historical navigation adaptation.
   */
  private async executeWarmupPipeline(userId: string | number): Promise<void> {
    const promoted = await this.getPromotedModules(userId);
    
    // Default tiers
    let tier1: CacheModule[] = ["profile", "notifications", "resume"];
    let tier2: CacheModule[] = ["jobs", "lms"];
    let tier3: CacheModule[] = ["messages", "skill_lab", "hackathons"];

    // Adapt tiers: Promote the top 2 historically active modules to Tier 1
    promoted.slice(0, 2).forEach((mod) => {
      // Remove from tier 2/3
      tier2 = tier2.filter((m) => m !== mod);
      tier3 = tier3.filter((m) => m !== mod);
      // Insert into tier 1 if not already present
      if (!tier1.includes(mod)) {
        tier1.push(mod);
      }
    });

    logger.info({ userId, tier1, tier2, tier3 }, "Warmup tier allocations finalized");

    const userRoom = `user:${userId}`;

    // --- TIER 1: Immediate Parallel Warmup ---
    logger.info({ userId }, "Executing Tier 1 Warmup (Profile, Notifications, Resume)");
    await Promise.all(tier1.map((mod) => this.warmModule(userId, mod)));
    logger.info({ userId }, "Tier 1 Warmup complete");
    await webSocketSyncService.publishToPubSub(userRoom, "warmup:tier_complete", { tier: 1 });

    // --- TIER 2: Executed after 2-second delay ---
    await new Promise((resolve) => setTimeout(resolve, 2000));
    logger.info({ userId }, "Executing Tier 2 Warmup (Jobs, LMS)");
    await Promise.all(tier2.map((mod) => this.warmModule(userId, mod)));
    logger.info({ userId }, "Tier 2 Warmup complete");
    await webSocketSyncService.publishToPubSub(userRoom, "warmup:tier_complete", { tier: 2 });

    // --- TIER 3: Executed after 5-second delay ---
    await new Promise((resolve) => setTimeout(resolve, 3000)); // 2s + 3s = 5s total
    logger.info({ userId }, "Executing Tier 3 Warmup (Messages, Certificates, Skill Lab)");
    await Promise.all(tier3.map((mod) => this.warmModule(userId, mod)));
    logger.info({ userId }, "Tier 3 Warmup complete");
    await webSocketSyncService.publishToPubSub(userRoom, "warmup:tier_complete", { tier: 3 });

    logger.info({ userId }, "All login cache warmup tiers completed successfully");
  }

  /**
   * Simulates fetching clean profile/entity records from DB/Agents and writing them to Redis.
   * In a real implementation, this references specific database client utilities.
   */
  private async warmModule(userId: string | number, module: CacheModule): Promise<void> {
    try {
      let key = "";
      let mockData: any = {};
      let entity = "";

      if (module === "profile") {
        entity = "data";
        key = CacheKeyRegistry.getKey(module, entity, userId);
        mockData = { userId, fullName: "Alex Candidate", email: "alex@vidyamarg.ai", role: "candidate" };
      } else if (module === "notifications") {
        entity = "list";
        key = CacheKeyRegistry.getKey(module, entity, userId);
        mockData = [
          { id: 1, title: "Welcome to VidyamargAI", message: "Upload your resume to get started!", read: false },
        ];
      } else if (module === "resume") {
        entity = "data";
        key = CacheKeyRegistry.getKey(module, entity, userId);
        mockData = { parsedName: "Alex Candidate", skills: "Python, SQL, TypeScript", summary: "Senior Dev" };
      } else if (module === "jobs") {
        entity = "matched";
        key = CacheKeyRegistry.getKey(module, entity, userId);
        mockData = [
          { id: 101, title: "Fastify Engineer", company: "Meta", score: 95 },
          { id: 102, title: "Redis Platform Developer", company: "Stripe", score: 92 },
        ];
      } else if (module === "lms") {
        entity = "progress";
        key = CacheKeyRegistry.getKey(module, entity, userId, "course_123");
        mockData = { courseId: "course_123", progress: 75, completedLessons: ["lesson_1", "lesson_2"] };
      } else {
        entity = "index";
        key = CacheKeyRegistry.getKey(module, entity, userId);
        mockData = { status: "initialized", timestamp: Date.now() };
      }

      const ttlConfig = CacheKeyRegistry.getTTL(module, entity);
      const version = 1; // default version
      await cacheInvalidationService.set(key, mockData, ttlConfig, version);
      logger.debug({ userId, module, key }, "Warmed module cache successfully");
    } catch (err: any) {
      logger.error({ userId, module, error: err.message }, "Failed to warm module cache");
    }
  }
}

export const loginWarmupService = new LoginWarmupService();
export default loginWarmupService;
