export interface CacheTTLConfig {
  freshTTL: number; // in seconds
  staleTTL: number; // in seconds
}

export const CACHE_VERSIONS = {
  resume: 2,
  jobs: 1,
  ai_chat: 1,
  messages: 1,
  notifications: 1,
  lms: 3,
  profile: 1,
  hackathons: 1,
  skill_lab: 1,
  course_generation: 1,
  quiz_generation: 1,
  interview_generation: 1,
} as const;

export type CacheModule = keyof typeof CACHE_VERSIONS;

export const CACHE_TTLS: Record<string, CacheTTLConfig> = {
  // Resume Builder
  "resume:data": { freshTTL: 3600, staleTTL: 86400 }, // 1h fresh, 24h stale
  "resume:ats_score": { freshTTL: 3600, staleTTL: 86400 },
  "resume:missing_skills": { freshTTL: 3600, staleTTL: 86400 },
  "resume:recommended_courses": { freshTTL: 3600, staleTTL: 86400 },
  "resume:recommended_jobs": { freshTTL: 3600, staleTTL: 86400 },
  "resume:ai_feedback": { freshTTL: 3600, staleTTL: 86400 },
  "resume:readiness_score": { freshTTL: 3600, staleTTL: 86400 },
  "resume:version": { freshTTL: 3600, staleTTL: 86400 },

  // Jobs Agent
  "jobs:matched": { freshTTL: 900, staleTTL: 7200 }, // 15min fresh, 2h stale
  "jobs:recommended": { freshTTL: 900, staleTTL: 7200 },
  "jobs:scores": { freshTTL: 900, staleTTL: 7200 },
  "jobs:refresh_meta": { freshTTL: 300, staleTTL: 1800 },

  // Ask Tush AI
  "ai_chat:session": { freshTTL: 1800, staleTTL: 604800 }, // 30min fresh, 7 days stale
  "ai_chat:index": { freshTTL: 1800, staleTTL: 604800 },
  "ai_chat:context": { freshTTL: 1800, staleTTL: 604800 },

  // Messages
  "messages:thread": { freshTTL: 300, staleTTL: 3600 }, // 5min fresh, 1h stale
  "messages:index": { freshTTL: 300, staleTTL: 3600 },
  "messages:unread": { freshTTL: 60, staleTTL: 900 },

  // Notifications
  "notifications:list": { freshTTL: 60, staleTTL: 900 }, // 1min fresh, 15min stale
  "notifications:unread": { freshTTL: 60, staleTTL: 900 },

  // User Profile
  "profile:data": { freshTTL: 1800, staleTTL: 86400 }, // 30min fresh, 24h stale

  // Hackathons
  "hackathons:list": { freshTTL: 1800, staleTTL: 86400 }, // 30min fresh, 24h stale
  "hackathons:details": { freshTTL: 3600, staleTTL: 86400 },

  // Skill Lab
  "skill_lab:assessments": { freshTTL: 3600, staleTTL: 86400 }, // 1h fresh, 24h stale
  "skill_lab:scores": { freshTTL: 1800, staleTTL: 86400 },

  // LMS
  "lms:course": { freshTTL: 86400, staleTTL: 604800 }, // 24h fresh, 7 days stale
  "lms:curriculum": { freshTTL: 86400, staleTTL: 604800 },
  "lms:module": { freshTTL: 86400, staleTTL: 604800 },
  "lms:topic": { freshTTL: 86400, staleTTL: 604800 },
  "lms:lesson": { freshTTL: 86400, staleTTL: 604800 },
  "lms:pdf": { freshTTL: 86400, staleTTL: 604800 },
  "lms:quiz": { freshTTL: 86400, staleTTL: 604800 },
  "lms:progress": { freshTTL: 300, staleTTL: 86400 }, // 5min fresh, 24h stale
  "lms:certificate": { freshTTL: 86400, staleTTL: 2592000 }, // 24h fresh, 30 days stale
  "lms:ai_interview": { freshTTL: 3600, staleTTL: 86400 }, // 1h fresh, 24h stale

  // Generation Agents
  "course_generation:outline": { freshTTL: 604800, staleTTL: 2592000 }, // 7 days fresh, 30 days stale
  "quiz_generation:quiz": { freshTTL: 604800, staleTTL: 2592000 },
  "interview_generation:questions": { freshTTL: 604800, staleTTL: 2592000 },
};

export class CacheKeyRegistry {
  /**
   * Generates a strongly-typed and versioned cache key.
   * Format: {module}:{entity}:v{version}:{id}
   */
  public static getKey(
    module: CacheModule,
    entity: string,
    id: string | number,
    additionalId?: string | number
  ): string {
    const version = CACHE_VERSIONS[module];
    const baseKey = `${module}:${entity}:v${version}:${id}`;
    return additionalId !== undefined ? `${baseKey}:${additionalId}` : baseKey;
  }

  /**
   * Returns the SWR TTL configurations (freshTTL and staleTTL) for a specific pattern/entity.
   */
  public static getTTL(module: CacheModule, entity: string): CacheTTLConfig {
    const registryKey = `${module}:${entity}`;
    const config = CACHE_TTLS[registryKey];
    if (!config) {
      logger.warn(`No TTL configuration found for cache key: ${registryKey}. Using default (5m/1h).`);
      return { freshTTL: 300, staleTTL: 3600 };
    }
    return config;
  }

  /**
   * Builds the redis glob pattern for cache invalidation.
   */
  public static getPattern(module: CacheModule, entity: string, id?: string | number): string {
    const version = CACHE_VERSIONS[module];
    if (id !== undefined) {
      return `${module}:${entity}:v${version}:${id}*`;
    }
    return `${module}:${entity}:v${version}:*`;
  }
}

import pino from "pino";
const logger = pino({ name: "cache-key-registry" });
