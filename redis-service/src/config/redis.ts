import Redis, { Cluster, RedisOptions, ClusterOptions } from "ioredis";
import pino from "pino";

const logger = pino({
  name: "redis-connection-manager",
  level: process.env.LOG_LEVEL || "info",
});

export interface MultiRegionConfig {
  primaryRegion: string;
  currentRegion: string;
  regionalReplicas: { [region: string]: string[] }; // region -> host:port strings
}

export class RedisConnectionManager {
  private primaryClient!: Redis | Cluster;
  private regionalReadClient!: Redis | Cluster;
  private isClusterMode: boolean = false;

  constructor() {
    this.initializeClients();
  }

  /**
   * Initializes Redis connections for writes (primary) and reads (replica/regional)
   */
  private initializeClients() {
    const mode = process.env.REDIS_MODE || "standalone"; // standalone | cluster | sentinel
    const useTls = process.env.REDIS_USE_TLS === "true";
    const password = process.env.REDIS_PASSWORD || undefined;
    const username = process.env.REDIS_USERNAME || undefined;

    const tlsOptions = useTls ? { rejectUnauthorized: false } : undefined;

    const commonOptions: RedisOptions = {
      username,
      password,
      tls: tlsOptions,
      keepAlive: 10000,
      connectTimeout: 10000,
      maxRetriesPerRequest: 3,
      retryStrategy(times) {
        const delay = Math.min(times * 100, 3000);
        logger.warn({ retryTimes: times, nextDelay: delay }, "Redis connection lost. Retrying connection...");
        return delay;
      },
    };

    if (mode === "cluster") {
      this.isClusterMode = true;
      const clusterNodes = (process.env.REDIS_CLUSTER_NODES || "localhost:6379")
        .split(",")
        .map((node) => {
          const [host, port] = node.split(":");
          return { host, port: parseInt(port || "6379", 10) };
        });

      const clusterOptions: ClusterOptions = {
        dnsLookup: (address, callback) => callback(null, address),
        scaleReads: "slave", // route read commands to replicas
        redisOptions: commonOptions,
        clusterRetryStrategy(times) {
          const delay = Math.min(times * 200, 5000);
          logger.warn({ retryTimes: times, nextDelay: delay }, "Redis Cluster connection lost. Retrying...");
          return delay;
        },
      };

      logger.info({ nodes: clusterNodes }, "Initializing Redis Cluster connection");
      this.primaryClient = new Redis.Cluster(clusterNodes, clusterOptions);
      this.regionalReadClient = this.primaryClient; // cluster client routes reads automatically to nearest slave
    } else if (mode === "sentinel") {
      const sentinelNodes = (process.env.REDIS_SENTINEL_NODES || "localhost:26379")
        .split(",")
        .map((node) => {
          const [host, port] = node.split(":");
          return { host, port: parseInt(port || "26379", 10) };
        });
      const masterName = process.env.REDIS_SENTINEL_MASTER_NAME || "mymaster";

      logger.info({ sentinels: sentinelNodes, masterName }, "Initializing Redis Sentinel connection");
      this.primaryClient = new Redis({
        ...commonOptions,
        sentinels: sentinelNodes,
        name: masterName,
        role: "master",
      });

      // Regional replica routing under Sentinel mode
      const currentRegion = process.env.CURRENT_REGION || "us-east-1";
      const regionalReplicaHost = process.env[`REDIS_REPLICA_HOST_${currentRegion.toUpperCase().replace("-", "_")}`];
      
      if (regionalReplicaHost) {
        const [host, port] = regionalReplicaHost.split(":");
        logger.info({ host, port }, "Connecting to local Sentinel read replica");
        this.regionalReadClient = new Redis({
          ...commonOptions,
          host,
          port: parseInt(port || "6379", 10),
          role: "slave",
        });
      } else {
        this.regionalReadClient = new Redis({
          ...commonOptions,
          sentinels: sentinelNodes,
          name: masterName,
          role: "slave",
        });
      }
    } else {
      // Standalone mode with regional read replicas
      const host = process.env.REDIS_HOST || "localhost";
      const port = parseInt(process.env.REDIS_PORT || "6379", 10);

      logger.info({ host, port }, "Initializing Standalone Redis Connection");
      this.primaryClient = new Redis({
        ...commonOptions,
        host,
        port,
      });

      const currentRegion = process.env.CURRENT_REGION || "us-east-1";
      const regionalReplicaHost = process.env[`REDIS_REPLICA_HOST_${currentRegion.toUpperCase().replace("-", "_")}`];

      if (regionalReplicaHost) {
        const [rHost, rPort] = regionalReplicaHost.split(":");
        logger.info({ rHost, rPort, region: currentRegion }, "Connecting to regional read replica for standalone mode");
        this.regionalReadClient = new Redis({
          ...commonOptions,
          host: rHost,
          port: parseInt(rPort || "6379", 10),
        });
      } else {
        this.regionalReadClient = this.primaryClient;
      }
    }

    this.registerEventHandlers();
  }

  private registerEventHandlers() {
    const clients = [
      { name: "Primary Client", client: this.primaryClient },
      { name: "Regional Read Client", client: this.regionalReadClient },
    ];

    clients.forEach(({ name, client }) => {
      client.on("connect", () => {
        logger.info({ client: name }, "Successfully connected to Redis server");
      });
      client.on("ready", () => {
        logger.info({ client: name }, "Redis client is ready to accept commands");
      });
      client.on("error", (err) => {
        logger.error({ client: name, error: err.message }, "Redis connection error occurred");
      });
      client.on("close", () => {
        logger.warn({ client: name }, "Redis connection closed");
      });
    });
  }

  /**
   * Returns client instance for writes
   */
  public getWritableClient(): Redis | Cluster {
    return this.primaryClient;
  }

  /**
   * Returns client instance for reads (local replica preferred)
   */
  public getReadableClient(): Redis | Cluster {
    return this.regionalReadClient;
  }

  /**
   * Gracefully shuts down all Redis connections
   */
  public async closeConnections(): Promise<void> {
    logger.info("Closing all Redis connections");
    await Promise.all([
      this.primaryClient.quit().catch(() => {}),
      this.regionalReadClient.quit().catch(() => {}),
    ]);
  }
}

export const redisConnectionManager = new RedisConnectionManager();
export default redisConnectionManager;
