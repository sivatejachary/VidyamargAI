import { Cluster } from "ioredis";
import Redis from "ioredis";
import redisConnectionManager from "../config/redis";
import pino from "pino";

const logger = pino({
  name: "redis-streams-event-bus",
  level: process.env.LOG_LEVEL || "info",
});

export type DomainEventType =
  | "ResumeUploaded"
  | "ResumeUpdated"
  | "JobApplied"
  | "CourseCompleted"
  | "LessonCompleted"
  | "QuizSubmitted"
  | "CertificateIssued"
  | "ProfileUpdated"
  | "MessageSent"
  | "NotificationCreated"
  | "TeamCreated"
  | "HackathonJoined"
  | "AssessmentSubmitted";

export interface DomainEventPayload {
  eventId: string;
  eventType: DomainEventType;
  userId: string | number;
  timestamp: number;
  data: Record<string, any>;
}

export class RedisEventBus {
  private redis: Redis | Cluster;
  private streamName = "global:domain_events";
  private dlqStreamName = "global:dlq_events";

  constructor() {
    this.redis = redisConnectionManager.getWritableClient();
  }

  /**
   * Publishes a domain event into the global Redis Stream (XADD)
   */
  public async publish(eventType: DomainEventType, userId: string | number, data: Record<string, any>): Promise<string> {
    const eventPayload: DomainEventPayload = {
      eventId: `${eventType}:${userId}:${Date.now()}:${Math.random().toString(36).substr(2, 9)}`,
      eventType,
      userId,
      timestamp: Math.floor(Date.now() / 1000),
      data,
    };

    try {
      // Append event payload to the Redis stream (MAXLEN of 100000 to prevent memory growth)
      const messageId = await this.redis.xadd(
        this.streamName,
        "MAXLEN",
        "~",
        "100000",
        "*",
        "payload",
        JSON.stringify(eventPayload)
      );
      logger.info({ eventType, userId, messageId }, "Event published successfully to Redis Stream");
      return messageId || "";
    } catch (err: any) {
      logger.error({ eventType, userId, error: err.message }, "Failed to publish event to Redis Stream");
      throw err;
    }
  }

  /**
   * Creates a consumer group for a stream (XGROUP CREATE)
   */
  public async createConsumerGroup(groupName: string): Promise<void> {
    try {
      // Create group starting at the beginning of the stream ($ for new messages only, 0 for all)
      await this.redis.xgroup("CREATE", this.streamName, groupName, "$", "MKSTREAM");
      logger.info({ groupName }, "Created new consumer group");
    } catch (err: any) {
      if (err.message.includes("BUSYGROUP")) {
        logger.debug({ groupName }, "Consumer group already exists (BUSYGROUP). Skipping creation.");
      } else {
        logger.error({ groupName, error: err.message }, "Failed to create consumer group");
      }
    }
  }

  /**
   * Listens for new messages in the stream under a consumer group context (XREADGROUP)
   */
  public async listen(
    groupName: string,
    consumerName: string,
    onMessage: (event: DomainEventPayload) => Promise<void>
  ): Promise<void> {
    await this.createConsumerGroup(groupName);

    logger.info({ groupName, consumerName }, "Redis Stream event consumer started listening");

    const poll = async () => {
      try {
        // Read unread messages ('>' means new messages, which haven't been delivered to other consumers)
        const results = await this.redis.xreadgroup(
          "GROUP",
          groupName,
          consumerName,
          "COUNT",
          "10",
          "BLOCK",
          "2000",
          "STREAMS",
          this.streamName,
          ">"
        );

        if (results && results.length > 0) {
          const streamEntries = results[0][1];
          for (const entry of streamEntries) {
            const [messageId, fields] = entry;
            const payloadIndex = fields.indexOf("payload");
            if (payloadIndex !== -1) {
              const payloadStr = fields[payloadIndex + 1];
              const event: DomainEventPayload = JSON.parse(payloadStr);

              try {
                // Process the event
                await onMessage(event);
                // Acknowledge the message (XACK) to remove it from the PEL (Pending Entries List)
                await this.redis.xack(this.streamName, groupName, messageId);
                logger.debug({ messageId, eventType: event.eventType }, "Acknowledged event message");
              } catch (processError: any) {
                logger.error({ messageId, error: processError.message }, "Error processing stream message. Sending to DLQ retry queue.");
                await this.handleDeadLetter(groupName, messageId, event);
              }
            }
          }
        }
      } catch (err: any) {
        logger.error({ error: err.message }, "Error during Redis Stream poll operation");
      }

      // Re-trigger poll loop
      setTimeout(poll, 100);
    };

    poll();
    this.startPendingRetryMonitor(groupName, consumerName, onMessage);
  }

  /**
   * Moves a failed stream entry to the Dead Letter Queue (DLQ) and acknowledges the original message.
   */
  private async handleDeadLetter(groupName: string, messageId: string, event: DomainEventPayload): Promise<void> {
    try {
      const dlqPayload = {
        originalMessageId: messageId,
        groupName,
        failedAt: Math.floor(Date.now() / 1000),
        event,
      };

      await this.redis.xadd(this.dlqStreamName, "MAXLEN", "~", "50000", "*", "payload", JSON.stringify(dlqPayload));
      // Acknowledge the original message in the primary stream so it doesn't get stuck in PEL
      await this.redis.xack(this.streamName, groupName, messageId);
      logger.warn({ messageId, eventId: event.eventId }, "Failed stream message forwarded to DLQ and acknowledged");
    } catch (dlqErr: any) {
      logger.error({ messageId, error: dlqErr.message }, "Failed to route failed message to DLQ");
    }
  }

  /**
   * Monitor for messages stuck in the Pending Entries List (PEL) for longer than 30s.
   * Retries them, or routes them to DLQ if they exceed 3 delivery attempts.
   */
  private async startPendingRetryMonitor(
    groupName: string,
    consumerName: string,
    onMessage: (event: DomainEventPayload) => Promise<void>
  ): Promise<void> {
    const checkPending = async () => {
      try {
        // Read pending list details: XPENDING <stream> <group> [<start> <end> <count> [<consumer>]]
        const pendingList = await this.redis.xpending(
          this.streamName,
          groupName,
          "-",
          "+",
          10
        ) as any[];

        if (pendingList && pendingList.length > 0) {
          for (const pendingInfo of pendingList) {
            const [messageId, consumer, idleTime, deliveryCount] = pendingInfo;

            // If idle for more than 30 seconds (30000ms)
            if (idleTime > 30000) {
              logger.warn({ messageId, consumer, idleTime, deliveryCount }, "Stale pending message detected");

              if (deliveryCount > 3) {
                logger.error({ messageId }, "Message exceeded 3 retry attempts. Discarding to DLQ.");
                // Fetch full payload to write to DLQ
                const entries = await this.redis.xrange(this.streamName, messageId, messageId);
                if (entries && entries.length > 0) {
                  const fields = entries[0][1];
                  const payloadIndex = fields.indexOf("payload");
                  if (payloadIndex !== -1) {
                    const event: DomainEventPayload = JSON.parse(fields[payloadIndex + 1]);
                    await this.handleDeadLetter(groupName, messageId, event);
                  }
                } else {
                  // If entry can't be fetched, still acknowledge to remove from PEL
                  await this.redis.xack(this.streamName, groupName, messageId);
                }
              } else {
                // Claim the message (XCLAIM) to re-process under this consumer
                const claimed = await this.redis.xclaim(
                  this.streamName,
                  groupName,
                  consumerName,
                  30000, // min-idle-time
                  messageId
                );

                if (claimed && claimed.length > 0) {
                  const fields = claimed[0][1];
                  const payloadIndex = fields.indexOf("payload");
                  if (payloadIndex !== -1) {
                    const event: DomainEventPayload = JSON.parse(fields[payloadIndex + 1]);
                    logger.info({ messageId }, "Re-claiming and retrying message execution");
                    await onMessage(event);
                    await this.redis.xack(this.streamName, groupName, messageId);
                  }
                }
              }
            }
          }
        }
      } catch (err: any) {
        logger.error({ error: err.message }, "Error monitoring pending stream entries");
      }

      // Check PEL every 60 seconds
      setTimeout(checkPending, 60000);
    };

    // Delay first PEL check by 60s
    setTimeout(checkPending, 60000);
  }
}

export const eventBus = new RedisEventBus();
export default eventBus;
