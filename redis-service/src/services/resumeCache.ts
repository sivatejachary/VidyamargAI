import crypto from "crypto";
import { lockService } from "./lock";
import cacheInvalidationService from "./invalidation";
import webSocketSyncService from "./websocket";
import eventBus from "./streams";
import { CacheKeyRegistry } from "../config/versions";
import pino from "pino";

const logger = pino({
  name: "resume-cache-service",
  level: process.env.LOG_LEVEL || "info",
});

export interface ResumeData {
  name: string;
  email: string;
  phone: string;
  summary: string;
  skills: string[];
  experience: any[];
  education: any[];
  projects: any[];
  certifications: string[];
  achievements: string[];
  languages: string[];
  github?: string;
  linkedin?: string;
  portfolio?: string;
}

export interface AIQualityBreakdown {
  grammar: number;
  formatting: number;
  readability: number;
  project_quality: number;
  achievement_quality: number;
  structure: number;
}

export interface AIAnalysisResult {
  completionScore: number;
  missingItems: string[];
  aiQualityScore: number;
  aiQualityBreakdown: AIQualityBreakdown;
  skillsExtracted: string[];
  missingSkills: string[];
  recommendedCourses: string[];
  lastUpdated: number;
}

export class ResumeCacheService {
  /**
   * Generates a hash signature of the PDF file content.
   */
  public calculateFileHash(content: Buffer): string {
    return crypto.createHash("sha256").update(content).digest("hex");
  }

  /**
   * Checks if the uploaded resume matches the currently cached version.
   */
  public async checkVersion(userId: string | number, fileHash: string): Promise<boolean> {
    const versionKey = CacheKeyRegistry.getKey("resume", "version", userId);
    try {
      const envelope = await cacheInvalidationService.get<string>(
        "resume",
        "version",
        userId,
        async () => ""
      );
      return envelope === fileHash;
    } catch {
      return false;
    }
  }

  /**
   * Processes a resume upload: Gates parsing via version checks, acquires distributed locks,
   * runs AI analysis, populates Postgres & Redis caches, and syncs all devices.
   */
  public async processResumeUpload(
    userId: string | number,
    fileContent: Buffer,
    filename: string
  ): Promise<AIAnalysisResult> {
    const fileHash = this.calculateFileHash(fileContent);

    // 1. Version check: Stop and return cached data immediately if file hasn't changed
    const isCached = await this.checkVersion(userId, fileHash);
    if (isCached) {
      logger.info({ userId, filename }, "Cache Hit: Resume version matches. Skipping AI parsing.");
      const analysisKey = CacheKeyRegistry.getKey("resume", "ai_feedback", userId);
      const cachedAnalysis = await cacheInvalidationService.get<AIAnalysisResult>(
        "resume",
        "ai_feedback",
        userId,
        async () => { throw new Error("Stale analysis missing from cache"); }
      );
      return cachedAnalysis;
    }

    // 2. Mismatch: Acquire distributed rebuild lock to prevent parallel parses for same user
    logger.info({ userId, filename }, "Cache Miss: New resume version detected. Acquiring rebuild lock.");
    const lockSession = await lockService.acquire("resume", userId);
    if (!lockSession) {
      logger.warn({ userId }, "Failed to acquire resume build lock. Another process is parsing.");
      throw new Error("Resume processing already in progress. Please wait.");
    }

    try {
      // Re-verify version under lock context (Double-Checked Locking pattern)
      const isCachedUnderLock = await this.checkVersion(userId, fileHash);
      if (isCachedUnderLock) {
        logger.info({ userId }, "Re-verification under lock hit cache. Releasing lock.");
        const analysisKey = CacheKeyRegistry.getKey("resume", "ai_feedback", userId);
        return await cacheInvalidationService.get<AIAnalysisResult>(
          "resume",
          "ai_feedback",
          userId,
          async () => { throw new Error("Analysis missing"); }
        );
      }

      // 3. AI Extraction Gate: Run Gemini parsing exactly once per version
      logger.info({ userId }, "Invoking AI resume parsing agents");
      const parsedResume = await this.runAIParsingAgent(fileContent);

      // 4. Calculate AI Quality and completions metrics
      const analysisResult = this.evaluateResumeQuality(parsedResume);

      // 5. Persist to PostgreSQL (Mocked database save operation)
      await this.saveProfileToPostgres(userId, parsedResume, analysisResult);

      // 6. Write versioned keys atomically to Redis
      const version = 2; // match CACHE_VERSIONS
      const ttl = CacheKeyRegistry.getTTL("resume", "data");

      await Promise.all([
        cacheInvalidationService.set(CacheKeyRegistry.getKey("resume", "data", userId), parsedResume, ttl, version),
        cacheInvalidationService.set(CacheKeyRegistry.getKey("resume", "ai_feedback", userId), analysisResult, ttl, version),
        cacheInvalidationService.set(CacheKeyRegistry.getKey("resume", "version", userId), fileHash, ttl, version),
        cacheInvalidationService.set(CacheKeyRegistry.getKey("resume", "missing_skills", userId), analysisResult.missingSkills, ttl, version),
      ]);

      // 7. Publish Domain Event to Redis Streams
      await eventBus.publish("ResumeUploaded", userId, {
        filename,
        fileHash,
        skillsCount: parsedResume.skills.length,
        qualityScore: analysisResult.aiQualityScore,
      });

      // 8. Broadcast websocket sync event to all active candidate devices (instant display sync)
      const userRoom = `user:${userId}`;
      await webSocketSyncService.publishToPubSub(userRoom, "resume:sync", {
        message: "Your resume profile has been updated by AI!",
        data: parsedResume,
        analysis: analysisResult,
      });

      logger.info({ userId }, "Resume upload processing and cross-device sync completed");
      return analysisResult;
    } finally {
      // Release distributed lock
      await lockService.release(lockSession);
    }
  }

  /**
   * Mock AI Agent invoker mimicking parsed output payload.
   */
  private async runAIParsingAgent(content: Buffer): Promise<ResumeData> {
    // Simulate AI extraction latency (Gemini/NVIDIA)
    await new Promise((resolve) => setTimeout(resolve, 800));

    return {
      name: "Alex Candidate",
      email: "alex@vidyamarg.ai",
      phone: "9876543210",
      summary: "Passionate Software Engineer with experience in TypeScript, Node.js, and Redis caching layers.",
      skills: ["TypeScript", "Node.js", "Redis", "PostgreSQL", "Docker", "Express"],
      experience: [
        { role: "Backend Developer", company: "Tech Solutions", years: 3, description: "Maintained APIs" },
      ],
      education: [
        { degree: "B.Tech Computer Science", school: "Engineering College", year: 2024 },
      ],
      projects: [
        { name: "VidyamargAI", description: "Job matching platform", technologies: ["Next.js", "Fastify"] },
      ],
      certifications: ["AWS Cloud Practitioner"],
      achievements: ["Hackathon Winner 2025"],
      languages: ["English", "Hindi"],
      github: "https://github.com/alexcandidate",
      linkedin: "https://linkedin.com/in/alexcandidate",
    };
  }

  /**
   * Heuristic / AI quality analyzer computing completion and missing sections.
   */
  private evaluateResumeQuality(data: ResumeData): AIAnalysisResult {
    const missingItems: string[] = [];
    let completionCount = 0;
    const totalFields = 8;

    if (data.name) completionCount++; else missingItems.push("Name");
    if (data.phone) completionCount++; else missingItems.push("Contact Details");
    if (data.skills.length > 0) completionCount++; else missingItems.push("Skills");
    if (data.experience.length > 0) completionCount++; else missingItems.push("Experience");
    if (data.education.length > 0) completionCount++; else missingItems.push("Education");
    if (data.projects.length > 0) completionCount++; else missingItems.push("Projects");
    if (data.certifications.length > 0) completionCount++; else missingItems.push("Certifications");
    if (data.summary) completionCount++; else missingItems.push("Profile Summary");

    const completionScore = Math.round((completionCount / totalFields) * 100);

    const breakdown: AIQualityBreakdown = {
      grammar: 8,
      formatting: 9,
      readability: 9,
      project_quality: 7,
      achievement_quality: 8,
      structure: 9,
    };

    const aiQualityScore = Math.round(
      (breakdown.grammar +
        breakdown.formatting +
        breakdown.readability +
        breakdown.project_quality +
        breakdown.achievement_quality +
        breakdown.structure) / 6
    );

    const highDemandSkills = ["TypeScript", "Redis", "BullMQ", "Kubernetes", "Rust"];
    const missingSkills = highDemandSkills.filter((s) => !data.skills.includes(s));

    return {
      completionScore,
      missingItems,
      aiQualityScore,
      aiQualityBreakdown: breakdown,
      skillsExtracted: data.skills,
      missingSkills,
      recommendedCourses: ["Redis Masterclass", "System Design & Scaling"],
      lastUpdated: Math.floor(Date.now() / 1000),
    };
  }

  /**
   * Mock PostgreSQL persistence method.
   */
  private async saveProfileToPostgres(userId: string | number, resume: ResumeData, analysis: AIAnalysisResult): Promise<void> {
    // In production, this maps variables to:
    // await prisma.candidate.update({ where: { userId }, data: { ... } })
    logger.debug({ userId }, "Saved parsed resume profile records to PostgreSQL database");
  }
}

export const resumeCacheService = new ResumeCacheService();
export default resumeCacheService;
