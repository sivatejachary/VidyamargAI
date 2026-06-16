import { Cluster } from "ioredis";
import Redis from "ioredis";
import redisConnectionManager from "../config/redis";
import eventBus from "./streams";
import pino from "pino";

const logger = pino({
  name: "redis-distributed-lock",
  level: process.env.LOG_LEVEL || "info",
});

export const LOCK_TTLS = {
  resume: 15000,          // 15 seconds
  jobs: 30000,            // 30 seconds
  course_generation: 120000, // 120 seconds
  interview_generation: 90000, // 90 seconds
} as const;

export type LockType = keyof typeof LOCK_TTLS;

export interface LockSession {
  key: string;
  value: string;
  ttl: number;
}

export class RedisLockService {
  private redis: Redis | Cluster;

  constructor() {
    this.redis = redisConnectionManager.getWritableClient();
  }

  /**
   * Acquires a distributed lock using SET NX PX command.
   * Includes exponential backoff retries with jitter.
   */
  public async acquire(
    type: LockType,
    id: string | number,
    retryAttempts = 3,
    baseDelayMs = 100
  ): Promise<LockSession | null> {
    const key = `lock:${type}:${id}`;
    const value = `${Date.now()}:${Math.random().toString(36).substr(2, 9)}`;
    const ttl = LOCK_TTLS[type];

    let attempts = 0;
    while (attempts <= retryAttempts) {
      try {
        // SET key value NX (only if not exists) PX (with expire time in ms)
        const result = await this.redis.set(key, value, "NX", "PX", ttl);
        if (result === "OK") {
          logger.info({ key, value, ttl }, "Acquired distributed lock");
          return { key, value, ttl };
        }
      } catch (err: any) {
        logger.error({ key, error: err.message }, "Error attempting to acquire distributed lock");
      }

      attempts++;
      if (attempts <= retryAttempts) {
        // Jittered exponential backoff: baseDelay * 2^attempt + random(0, 50)
        const delay = baseDelayMs * Math.pow(2, attempts) + Math.floor(Math.random() * 50);
        logger.debug({ key, attempt: attempts, delay }, "Failed to acquire lock. Retrying after delay...");
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    logger.warn({ key, retryAttempts }, "Failed to acquire distributed lock after all retry attempts");
    return null;
  }

  /**
   * Releases a distributed lock atomically using a Lua script.
   * Ensures that a client can only delete its own lock, not another client's lock.
   */
  public async release(session: LockSession): Promise<boolean> {
    const { key, value } = session;
    
    // Lua script: Check if current value matches lock owner value. If yes, delete it.
    const luaScript = `
      if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
      else
        return 0
      end
    `;

    try {
      const result = await this.redis.eval(luaScript, 1, key, value);
      const released = Number(result) === 1;
      
      if (released) {
        logger.info({ key }, "Released distributed lock successfully");
      } else {
        logger.warn({ key, value }, "Attempted to release lock, but value did not match or lock expired");
      }
      return released;
    } catch (err: any) {
      logger.error({ key, error: err.message }, "Error releasing distributed lock");
      // Fallback: Send lock error telemetry to DLQ
      await this.reportLockFailureToDLQ(key, value, "Release error: " + err.message);
      return false;
    }
  }

  /**
   * Extends the lease of an active distributed lock atomically using a Lua script.
   */
  public async extend(session: LockSession, additionalTtlMs: number): Promise<boolean> {
    const { key, value } = session;

    // Lua script: Check value. If matches, reset TTL.
    const luaScript = `
      if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("pexpire", KEYS[1], ARGV[2])
      else
        return 0
      end
    `;

    try {
      const result = await this.redis.eval(luaScript, 1, key, value, additionalTtlMs);
      const extended = Number(result) === 1;
      
      if (extended) {
        logger.info({ key, additionalTtlMs }, "Extended distributed lock lease");
      } else {
        logger.warn({ key }, "Failed to extend distributed lock lease: lock expired or value mismatch");
      }
      return extended;
    } catch (err: any) {
      logger.error({ key, error: err.message }, "Error extending distributed lock lease");
      return false;
    }
  }

  /**
   * Helper to write lock failure logs to the DLQ Stream for audit/alerting
   */
  private async reportLockFailureToDLQ(key: string, lockValue: string, reason: string): Promise<void> {
    try {
      const errorPayload = {
        eventId: `LockError:${key}:${Date.now()}`,
        eventType: "LockFailure",
        userId: "system",
        timestamp: Math.floor(Date.now() / 1000),
        data: {
          lockKey: key,
          lockValue,
          reason,
        },
      };
      
      await this.redis.xadd("global:dlq_events", "MAXLEN", "~", "50000", "*", "payload", JSON.stringify(errorPayload));
      logger.info({ key }, "Lock failure reported to global DLQ Stream successfully");
    } catch (dlqErr: any) {
      logger.error({ key, error: dlqErr.message }, "Failed to publish lock failure to DLQ stream");
    }
  }
}

export const lockService = new RedisLockService();
export default lockService;
