import { Server, Socket } from "socket.io";
import { Server as HttpServer } from "http";
import Redis from "ioredis";
import redisConnectionManager from "../config/redis";
import pino from "pino";

const logger = pino({
  name: "websocket-sync-service",
  level: process.env.LOG_LEVEL || "info",
});

export interface WebSocketEvent<T = any> {
  room: string;
  event: string;
  payload: T;
  senderId?: string | number;
}

export class WebSocketSyncService {
  private io!: Server;
  private pubClient!: Redis;
  private subClient!: Redis;
  private pubSubChannel = "cache_events:sync";

  constructor() {
    this.initializeRedisPubSub();
  }

  /**
   * Initializes the Socket.IO server instance on top of HTTP server.
   */
  public attachServer(server: HttpServer): void {
    this.io = new Server(server, {
      cors: {
        origin: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(",") : "*",
        methods: ["GET", "POST"],
      },
      pingTimeout: 30000,
      pingInterval: 10000,
      connectionStateRecovery: {
        // Allows clients to automatically recover missed packets upon reconnection
        maxDisconnectionDuration: 2 * 60 * 1000, // 2 minutes
      },
    });

    this.configureAuthMiddleware();
    this.configureConnections();
    this.startRedisSubscriptionListener();
  }

  /**
   * Configures JWT verification middleware for connections.
   */
  private configureAuthMiddleware(): void {
    this.io.use((socket: Socket, next) => {
      try {
        const authHeader = socket.handshake.auth?.token || socket.handshake.headers?.authorization;
        if (!authHeader) {
          logger.warn("WebSocket connection rejected: Missing authorization token");
          return next(new Error("Authentication failed: Missing token"));
        }

        // Mock/extract userId from JWT token
        // In production, replace with actual jwt.verify()
        const token = authHeader.replace("Bearer ", "").trim();
        const payload = this.decodeJwtPayload(token);

        if (!payload || !payload.id) {
          logger.warn("WebSocket connection rejected: Invalid token payload");
          return next(new Error("Authentication failed: Invalid payload"));
        }

        socket.data.userId = payload.id;
        socket.data.role = payload.role || "candidate";
        logger.info({ userId: socket.data.userId }, "WebSocket connection authenticated successfully");
        next();
      } catch (err: any) {
        logger.error({ error: err.message }, "WebSocket auth middleware execution error");
        next(new Error("Authentication failed"));
      }
    });
  }

  /**
   * Safe JWT payload extraction (decodes without full library verification for transport layers)
   */
  private decodeJwtPayload(token: string): { id: string | number; role?: string } | null {
    try {
      const parts = token.split(".");
      if (parts.length !== 3) return null;
      const base64Url = parts[1];
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = Buffer.from(base64, "base64").toString("utf8");
      return JSON.parse(jsonPayload);
    } catch {
      return null;
    }
  }

  /**
   * Handles authenticated Socket.IO connections and room assignments.
   */
  private configureConnections(): void {
    this.io.on("connection", (socket: Socket) => {
      const userId = socket.data.userId;
      
      // Auto-join personal user room
      const userRoom = `user:${userId}`;
      socket.join(userRoom);
      logger.info({ userId, socketId: socket.id, room: userRoom }, "Client auto-joined personal synchronization room");

      // Dynamic course room subscription
      socket.on("subscribe:course", (courseId: string) => {
        const courseRoom = `course:${courseId}`;
        socket.join(courseRoom);
        logger.info({ userId, socketId: socket.id, room: courseRoom }, "Client joined course updates room");
      });

      socket.on("unsubscribe:course", (courseId: string) => {
        const courseRoom = `course:${courseId}`;
        socket.leave(courseRoom);
        logger.info({ userId, socketId: socket.id, room: courseRoom }, "Client left course updates room");
      });

      // Dynamic chat thread subscription
      socket.on("subscribe:thread", (threadId: string) => {
        const threadRoom = `thread:${threadId}`;
        socket.join(threadRoom);
        logger.info({ userId, socketId: socket.id, room: threadRoom }, "Client joined chat thread room");
      });

      socket.on("unsubscribe:thread", (threadId: string) => {
        const threadRoom = `thread:${threadId}`;
        socket.leave(threadRoom);
        logger.info({ userId, socketId: socket.id, room: threadRoom }, "Client left chat thread room");
      });

      // Dynamic organization updates subscription (admins/recruiters)
      socket.on("subscribe:org", (orgId: string) => {
        const orgRoom = `org:${orgId}`;
        socket.join(orgRoom);
        logger.info({ userId, socketId: socket.id, room: orgRoom }, "Client joined organization updates room");
      });

      socket.on("disconnect", (reason) => {
        logger.info({ userId, socketId: socket.id, reason }, "Client disconnected from WebSocket Server");
      });
    });
  }

  /**
   * Sets up publication and subscription Redis clients
   */
  private initializeRedisPubSub(): void {
    const mode = process.env.REDIS_MODE || "standalone";
    const useTls = process.env.REDIS_USE_TLS === "true";
    const password = process.env.REDIS_PASSWORD || undefined;
    const username = process.env.REDIS_USERNAME || undefined;
    const tlsOptions = useTls ? { rejectUnauthorized: false } : undefined;

    const options = {
      username,
      password,
      tls: tlsOptions,
      keepAlive: 10000,
    };

    if (mode === "sentinel") {
      const sentinelNodes = (process.env.REDIS_SENTINEL_NODES || "localhost:26379")
        .split(",")
        .map((node) => {
          const [host, port] = node.split(":");
          return { host, port: parseInt(port || "26379", 10) };
        });
      const masterName = process.env.REDIS_SENTINEL_MASTER_NAME || "mymaster";

      this.pubClient = new Redis({ ...options, sentinels: sentinelNodes, name: masterName });
      this.subClient = new Redis({ ...options, sentinels: sentinelNodes, name: masterName });
    } else if (mode === "cluster") {
      const clusterNodes = (process.env.REDIS_CLUSTER_NODES || "localhost:6379")
        .split(",")
        .map((node) => {
          const [host, port] = node.split(":");
          return { host, port: parseInt(port || "6379", 10) };
        });
      this.pubClient = new Redis.Cluster(clusterNodes, { redisOptions: options }) as any;
      this.subClient = new Redis.Cluster(clusterNodes, { redisOptions: options }) as any;
    } else {
      const host = process.env.REDIS_HOST || "localhost";
      const port = parseInt(process.env.REDIS_PORT || "6379", 10);
      this.pubClient = new Redis({ ...options, host, port });
      this.subClient = new Redis({ ...options, host, port });
    }
  }

  /**
   * Publishes an event to Redis Pub/Sub channel. Used by microservices to trigger cross-device syncs.
   */
  public async publishToPubSub<T>(room: string, event: string, payload: T, senderId?: string | number): Promise<void> {
    try {
      const message: WebSocketEvent<T> = { room, event, payload, senderId };
      await this.pubClient.publish(this.pubSubChannel, JSON.stringify(message));
      logger.debug({ room, event }, "Successfully published sync message to Redis Pub/Sub");
    } catch (err: any) {
      logger.error({ room, event, error: err.message }, "Failed to publish sync message to Redis Pub/Sub");
    }
  }

  /**
   * Subscribes to Redis Pub/Sub channel and broadcasts incoming sync messages to Socket.IO clients.
   */
  private startRedisSubscriptionListener(): void {
    this.subClient.subscribe(this.pubSubChannel, (err) => {
      if (err) {
        logger.error({ error: err.message }, "Failed to subscribe to Redis Pub/Sub sync channel");
      } else {
        logger.info({ channel: this.pubSubChannel }, "Subscribed to Redis Pub/Sub sync channel");
      }
    });

    this.subClient.on("message", (channel, messageStr) => {
      if (channel === this.pubSubChannel) {
        try {
          const wsEvent: WebSocketEvent = JSON.parse(messageStr);
          logger.info({ room: wsEvent.room, event: wsEvent.event }, "Received Redis Pub/Sub sync event. Broadcasting to Socket.IO clients.");
          
          // Emit message to everyone in the target room except the sender
          let target = this.io.to(wsEvent.room);
          if (wsEvent.senderId) {
            // Find active socket for the sender id if they are connected on this node
            const sockets = Array.from(this.io.sockets.sockets.values());
            const senderSocket = sockets.find((s) => s.data.userId === wsEvent.senderId);
            if (senderSocket) {
              target = target.except(senderSocket.id) as any;
            }
          }
          target.emit(wsEvent.event, wsEvent.payload);
        } catch (parseErr: any) {
          logger.error({ error: parseErr.message }, "Failed to parse Redis Pub/Sub sync message payload");
        }
      }
    });
  }
}

export const webSocketSyncService = new WebSocketSyncService();
export default webSocketSyncService;
