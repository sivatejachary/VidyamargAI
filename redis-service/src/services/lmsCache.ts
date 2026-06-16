import cacheInvalidationService from "./invalidation";
import webSocketSyncService from "./websocket";
import eventBus from "./streams";
import { CacheKeyRegistry } from "../config/versions";
import pino from "pino";

const logger = pino({
  name: "lms-cache-service",
  level: process.env.LOG_LEVEL || "info",
});

export interface CourseCurriculum {
  courseId: string;
  title: string;
  modules: Array<{
    id: string;
    title: string;
    lessons: Array<{ id: string; title: string; duration: string }>;
    quizzes: Array<{ id: string; title: string; questionsCount: number }>;
  }>;
}

export interface UserProgress {
  userId: string | number;
  courseId: string;
  progress: number; // percentage completed
  completedLessons: string[];
  completedQuizzes: Record<string, { score: number; passed: boolean }>;
}

export interface CertificateInfo {
  certificateId: string;
  courseId: string;
  courseTitle: string;
  userId: string | number;
  userName: string;
  code: string;
  earnedAt: number;
}

export class LMSCacheService {
  /**
   * Retrieves course curriculum structure.
   * Leverages SWR stale limit (fresh for 24h, stale for 7d).
   */
  public async getCourseCurriculum(courseId: string): Promise<CourseCurriculum> {
    return await cacheInvalidationService.get<CourseCurriculum>(
      "lms",
      "curriculum",
      courseId,
      async () => {
        logger.info({ courseId }, "Cache Miss: Querying course curriculum from database");
        return await this.fetchCurriculumFromPostgres(courseId);
      }
    );
  }

  /**
   * Retrieves candidate progress on a specific course.
   */
  public async getProgress(userId: string | number, courseId: string): Promise<UserProgress> {
    const progressKey = CacheKeyRegistry.getKey("lms", "progress", userId, courseId);
    return await cacheInvalidationService.get<UserProgress>(
      "lms",
      "progress",
      userId,
      async () => {
        logger.info({ userId, courseId }, "Cache Miss: Querying user course progress from database");
        return await this.fetchProgressFromPostgres(userId, courseId);
      },
      // Invalidation hook can trigger async refresh
    );
  }

  /**
   * Completes a course lesson: updates PostgreSQL, patches progress in Redis, and broadcasts to devices.
   */
  public async completeLesson(userId: string | number, courseId: string, lessonId: string): Promise<UserProgress> {
    const progressKey = CacheKeyRegistry.getKey("lms", "progress", userId, courseId);
    const ttlConfig = CacheKeyRegistry.getTTL("lms", "progress");
    const version = 3; // match CACHE_VERSIONS

    // 1. Fetch current progress
    const progress = await this.getProgress(userId, courseId);
    if (!progress.completedLessons.includes(lessonId)) {
      progress.completedLessons.push(lessonId);
    }

    // 2. Recalculate percentage based on curriculum lessons count
    const curriculum = await this.getCourseCurriculum(courseId);
    const totalLessons = curriculum.modules.reduce((acc, m) => acc + m.lessons.length, 0);
    progress.progress = totalLessons > 0 ? Math.round((progress.completedLessons.length / totalLessons) * 100) : 0;

    // 3. Persist to PostgreSQL (Mocked DB call)
    await this.updateProgressInPostgres(userId, courseId, progress.completedLessons, progress.progress);

    // 4. Update Redis Cache
    await cacheInvalidationService.set(progressKey, progress, ttlConfig, version);

    // 5. Publish Domain Event to Redis Streams
    await eventBus.publish("LessonCompleted", userId, {
      courseId,
      lessonId,
      progress: progress.progress,
    });

    // 6. Broadcast updated progress via WebSocket room (user personal room + course updates channel)
    const userRoom = `user:${userId}`;
    const courseRoom = `course:${courseId}`;

    const syncPayload = {
      courseId,
      progress: progress.progress,
      completedLessons: progress.completedLessons,
      completedQuizzes: progress.completedQuizzes,
    };

    await webSocketSyncService.publishToPubSub(userRoom, "lms:progress:sync", syncPayload);
    await webSocketSyncService.publishToPubSub(courseRoom, "course:activity", { userId, lessonId, action: "completed" });

    logger.info({ userId, courseId, lessonId, progress: progress.progress }, "Lesson completion processed and synced cross-device");
    return progress;
  }

  /**
   * Submits a quiz completion: updates progress metrics and syncs active displays.
   */
  public async submitQuiz(
    userId: string | number,
    courseId: string,
    quizId: string,
    score: number,
    passed: boolean
  ): Promise<UserProgress> {
    const progressKey = CacheKeyRegistry.getKey("lms", "progress", userId, courseId);
    const ttlConfig = CacheKeyRegistry.getTTL("lms", "progress");
    const version = 3;

    const progress = await this.getProgress(userId, courseId);
    progress.completedQuizzes[quizId] = { score, passed };

    await this.saveQuizAttemptInPostgres(userId, courseId, quizId, score, passed);
    await cacheInvalidationService.set(progressKey, progress, ttlConfig, version);

    await eventBus.publish("QuizSubmitted", userId, {
      courseId,
      quizId,
      score,
      passed,
    });

    const userRoom = `user:${userId}`;
    await webSocketSyncService.publishToPubSub(userRoom, "lms:progress:sync", {
      courseId,
      progress: progress.progress,
      completedLessons: progress.completedLessons,
      completedQuizzes: progress.completedQuizzes,
    });

    logger.info({ userId, courseId, quizId, score, passed }, "Quiz submission processed and synced successfully");
    return progress;
  }

  /**
   * Issues a course completion certificate: persists to DB, warms Redis cache, and triggers UI updates.
   */
  public async issueCertificate(
    userId: string | number,
    courseId: string,
    certificateCode: string
  ): Promise<CertificateInfo> {
    const certKey = CacheKeyRegistry.getKey("lms", "certificate", userId, courseId);
    const ttlConfig = CacheKeyRegistry.getTTL("lms", "certificate");
    const version = 3;

    const curriculum = await this.getCourseCurriculum(courseId);

    const certInfo: CertificateInfo = {
      certificateId: `CERT-${courseId.toUpperCase()}-${userId}-${Date.now()}`,
      courseId,
      courseTitle: curriculum.title,
      userId,
      userName: "Alex Candidate",
      code: certificateCode,
      earnedAt: Math.floor(Date.now() / 1000),
    };

    await this.saveCertificateInPostgres(certInfo);
    await cacheInvalidationService.set(certKey, certInfo, ttlConfig, version);

    await eventBus.publish("CertificateIssued", userId, {
      courseId,
      certificateId: certInfo.certificateId,
      code: certificateCode,
    });

    const userRoom = `user:${userId}`;
    await webSocketSyncService.publishToPubSub(userRoom, "lms:certificate:sync", certInfo);

    logger.info({ userId, courseId, certId: certInfo.certificateId }, "Certificate issued and synced across devices");
    return certInfo;
  }

  /**
   * Mock database query for course curriculum structure.
   */
  private async fetchCurriculumFromPostgres(courseId: string): Promise<CourseCurriculum> {
    await new Promise((resolve) => setTimeout(resolve, 200));
    return {
      courseId,
      title: "Full Stack Development & System Design",
      modules: [
        {
          id: "mod_1",
          title: "Module 1: Real-time Communication Layers",
          lessons: [
            { id: "lesson_1", title: "Introduction to WebSocket protocol", duration: "12:30" },
            { id: "lesson_2", title: "Scaling Socket.IO with Redis adapter", duration: "18:45" },
          ],
          quizzes: [
            { id: "quiz_1", title: "WebSockets and Pub/Sub Quiz", questionsCount: 5 },
          ],
        },
      ],
    };
  }

  /**
   * Mock database query for progress trackers.
   */
  private async fetchProgressFromPostgres(userId: string | number, courseId: string): Promise<UserProgress> {
    await new Promise((resolve) => setTimeout(resolve, 150));
    return {
      userId,
      courseId,
      progress: 0,
      completedLessons: [],
      completedQuizzes: {},
    };
  }

  // Mocks for DB operations
  private async updateProgressInPostgres(userId: string | number, courseId: string, completedLessons: string[], progress: number) {
    logger.debug({ userId, courseId, progress }, "Updated user course progress in PostgreSQL database");
  }
  private async saveQuizAttemptInPostgres(userId: string | number, courseId: string, quizId: string, score: number, passed: boolean) {
    logger.debug({ userId, quizId, score }, "Saved quiz score in PostgreSQL");
  }
  private async saveCertificateInPostgres(cert: CertificateInfo) {
    logger.debug({ certId: cert.certificateId }, "Created and saved certificate record in PostgreSQL");
  }
}

export const lmsCacheService = new LMSCacheService();
export default lmsCacheService;
