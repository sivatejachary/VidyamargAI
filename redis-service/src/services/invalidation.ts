import { Cluster } from "ioredis";
import Redis from "ioredis";
import redisConnectionManager from "../config/redis";
import { CacheKeyRegistry, CacheModule, CacheTTLConfig } from "../config/versions";
import pino from "pino";

const logger = pino({
  name: "cache-invalidation-service",
  level: process.env.LOG_LEVEL || "info",
});

export interface CacheEnvelope<T = any> {
  data: T;
  cachedAt: number; // Unix timestamp in seconds
  version: number;
}

export class CacheInvalidationService {
  private redis: Redis | Cluster;
  private inFlightRequests: Map<string, Promise<any>> = new Map();

  constructor() {
    this.redis = redisConnectionManager.getWritableClient();
  }

  /**
   * Retrieves data using SWR (Stale-While-Revalidate) flow with stampede protection.
   * If fresh: returns immediately.
   * If stale: returns stale immediately + triggers async rebuild.
   * If expired/missing: uses single-flight coalesced query to retrieve and cache.
   */
  public async get<T>(
    module: CacheModule,
    entity: string,
    id: string | number,
    dbQuery: () => Promise<T>,
    triggerBackgroundRevalidate?: (key: string) => void
  ): Promise<T> {
    const key = CacheKeyRegistry.getKey(module, entity, id);
    const ttlConfig = CacheKeyRegistry.getTTL(module, entity);
    const version = ttlConfig ? (ttlConfig as any).version || 1 : 1; // Fallback version if not defined

    try {
      const envelopeStr = await this.redis.get(key);
      if (envelopeStr) {
        const envelope: CacheEnvelope<T> = JSON.parse(envelopeStr);
        const age = Math.floor(Date.now() / 1000) - envelope.cachedAt;

        if (age < ttlConfig.freshTTL) {
          logger.debug({ key, age, freshTTL: ttlConfig.freshTTL }, "Cache Hit: Fresh");
          return envelope.data;
        }

        if (age < ttlConfig.staleTTL) {
          logger.info({ key, age, staleTTL: ttlConfig.staleTTL }, "Cache Hit: Stale (triggering background refresh)");
          if (triggerBackgroundRevalidate) {
            triggerBackgroundRevalidate(key);
          } else {
            this.rebuildBackground(key, dbQuery, ttlConfig, version);
          }
          return envelope.data;
        }

        logger.info({ key, age }, "Cache Miss: Expired beyond stale limit");
      }
    } catch (err: any) {
      logger.error({ key, error: err.message }, "Error reading from Redis. Falling back to DB query.");
    }

    // Cache Miss or Expired: Fetch with Single-Flight/Request Coalescing
    return this.coalesceRequest(key, dbQuery, ttlConfig, version);
  }

  /**
   * Deduplicates concurrent database reads for the same key.
   */
  private coalesceRequest<T>(
    key: string,
    dbQuery: () => Promise<T>,
    ttlConfig: CacheTTLConfig,
    version: number
  ): Promise<T> {
    const activePromise = this.inFlightRequests.get(key);
    if (activePromise) {
      logger.info({ key }, "Coalescing request (single-flight deduplication)");
      return activePromise;
    }

    const promise = dbQuery()
      .then(async (result) => {
        this.inFlightRequests.delete(key);
        // Save to cache in background
        await this.set(key, result, ttlConfig, version);
        return result;
      })
      .catch((err) => {
        this.inFlightRequests.delete(key);
        throw err;
      });

    this.inFlightRequests.set(key, promise);
    return promise;
  }

  /**
   * Serializes and stores data in Redis with custom envelope.
   */
  public async set<T>(
    key: string,
    data: T,
    ttlConfig: CacheTTLConfig,
    version: number
  ): Promise<void> {
    try {
      const envelope: CacheEnvelope<T> = {
        data,
        cachedAt: Math.floor(Date.now() / 1000),
        version,
      };
      // We set Redis TTL to staleTTL limit to allow SWR reading
      await this.redis.setex(key, ttlConfig.staleTTL, JSON.stringify(envelope));
      logger.debug({ key, staleTTL: ttlConfig.staleTTL }, "Successfully set Redis cache value");
    } catch (err: any) {
      logger.error({ key, error: err.message }, "Failed to write to Redis cache");
    }
  }

  /**
   * Rebuilds the cache in the background. Does not block the main SWR thread.
   */
  private async rebuildBackground<T>(
    key: string,
    dbQuery: () => Promise<T>,
    ttlConfig: CacheTTLConfig,
    version: number
  ): Promise<void> {
    // Implement rebuild lock check
    const lockKey = `lock:rebuild:${key}`;
    try {
      const acquired = await this.redis.set(lockKey, "1", "NX", "EX", 10);
      if (!acquired) {
        logger.debug({ key }, "Background rebuild already in progress. Skipping.");
        return;
      }

      logger.info({ key }, "Background rebuild started");
      const freshData = await dbQuery();
      await this.set(key, freshData, ttlConfig, version);
      await this.redis.del(lockKey);
      logger.info({ key }, "Background rebuild completed successfully");
    } catch (err: any) {
      logger.error({ key, error: err.message }, "Background rebuild failed");
      await this.redis.del(lockKey).catch(() => {});
    }
  }

  /**
   * Atomic Lua script invalidation for pattern matching (evicts stale keys)
   */
  public async invalidatePattern(pattern: string): Promise<number> {
    const luaScript = `
      local keys = redis.call('keys', ARGV[1])
      local count = 0
      for i, key in ipairs(keys) do
        redis.call('del', key)
        count = count + 1
      end
      return count
    `;

    try {
      const evictedCount = await this.redis.eval(luaScript, 0, pattern);
      logger.info({ pattern, evictedCount }, "Atomically invalidated Redis keys matching pattern");
      return Number(evictedCount);
    } catch (err: any) {
      logger.error({ pattern, error: err.message }, "Failed to execute Lua invalidation script");
      return 0;
    }
  }

  /**
   * Deletes a specific key directly.
   */
  public async delete(key: string): Promise<boolean> {
    try {
      const deleted = await this.redis.del(key);
      logger.info({ key, success: deleted > 0 }, "Deleted specific key from Redis");
      return deleted > 0;
    } catch (err: any) {
      logger.error({ key, error: err.message }, "Error deleting specific key");
      return false;
    }
  }
}

export const cacheInvalidationService = new CacheInvalidationService();
export default cacheInvalidationService;
