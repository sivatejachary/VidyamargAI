import cacheInvalidationService from "./invalidation";
import webSocketSyncService from "./websocket";
import eventBus from "./streams";
import { CacheKeyRegistry } from "../config/versions";
import pino from "pino";

const logger = pino({
  name: "ai-chat-cache-service",
  level: process.env.LOG_LEVEL || "info",
});

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
}

export interface ChatSessionMeta {
  chatId: string;
  title: string;
  createdAt: number;
  updatedAt: number;
}

export interface AIChatContext {
  userId: string | number;
  skills: string[];
  recentJobsViewed: string[];
  currentStep: string;
}

export class AIChatCacheService {
  /**
   * Retrieves all chat sessions metadata for a candidate.
   * Leverages SWR default config.
   */
  public async getChatIndex(userId: string | number): Promise<ChatSessionMeta[]> {
    return await cacheInvalidationService.get<ChatSessionMeta[]>(
      "ai_chat",
      "index",
      userId,
      async () => {
        logger.info({ userId }, "Cache Miss: Fetching chat sessions from database");
        return await this.fetchChatIndexFromPostgres(userId);
      }
    );
  }

  /**
   * Retrieves message thread history for a specific session.
   */
  public async getChatSession(userId: string | number, chatId: string): Promise<ChatMessage[]> {
    const key = CacheKeyRegistry.getKey("ai_chat", "session", userId, chatId);
    return await cacheInvalidationService.get<ChatMessage[]>(
      "ai_chat",
      "session",
      userId,
      async () => {
        logger.info({ userId, chatId }, "Cache Miss: Fetching message history from database");
        return await this.fetchChatSessionFromPostgres(chatId);
      },
      // Invalidation callback
    );
  }

  /**
   * Appends a new chat message to a session, updates index meta, and synchronizes devices.
   */
  public async saveChatMessage(
    userId: string | number,
    chatId: string,
    message: ChatMessage
  ): Promise<void> {
    const sessionKey = CacheKeyRegistry.getKey("ai_chat", "session", userId, chatId);
    const indexKey = CacheKeyRegistry.getKey("ai_chat", "index", userId);
    const ttlConfig = CacheKeyRegistry.getTTL("ai_chat", "session");
    const version = 1;

    try {
      // 1. Fetch current thread messages
      const messages = await this.getChatSession(userId, chatId);
      messages.push(message);

      // 2. Save back to Redis Cache
      await cacheInvalidationService.set(sessionKey, messages, ttlConfig, version);

      // 3. Update Chat Session Index Metadata
      const index = await this.getChatIndex(userId);
      let sessionMeta = index.find((s) => s.chatId === chatId);

      if (sessionMeta) {
        sessionMeta.updatedAt = Math.floor(Date.now() / 1000);
        // Update title dynamically if it was a default placeholder
        if (sessionMeta.title === "New Conversation" && message.role === "user") {
          sessionMeta.title = message.content.substring(0, 30) + "...";
        }
      } else {
        // Create new session entry
        sessionMeta = {
          chatId,
          title: message.role === "user" ? message.content.substring(0, 30) + "..." : "New Conversation",
          createdAt: Math.floor(Date.now() / 1000),
          updatedAt: Math.floor(Date.now() / 1000),
        };
        index.push(sessionMeta);
      }

      // Save updated index to Redis cache
      const indexTtl = CacheKeyRegistry.getTTL("ai_chat", "index");
      await cacheInvalidationService.set(indexKey, index, indexTtl, version);

      // 4. Publish Event to Redis Stream
      await eventBus.publish("MessageSent", userId, {
        chatId,
        messageId: message.id,
        role: message.role,
        length: message.content.length,
      });

      // 5. Broadcast message to all active devices listening in the thread room (real-time chat delivery)
      const threadRoom = `thread:${chatId}`;
      await webSocketSyncService.publishToPubSub(threadRoom, "message:new", {
        chatId,
        message,
      });

      // Also publish update to personal user room for sidebar updates
      const userRoom = `user:${userId}`;
      await webSocketSyncService.publishToPubSub(userRoom, "ai_chat:index_sync", index);

      logger.info({ userId, chatId, messageId: message.id }, "Successfully saved message and triggered cross-device synchronization");
    } catch (err: any) {
      logger.error({ userId, chatId, error: err.message }, "Failed to process and synchronize chat message");
    }
  }

  /**
   * Caches unified contextual info to prompt the AI model.
   */
  public async updateChatContext(
    userId: string | number,
    skills: string[],
    recentJobsViewed: string[],
    currentStep: string
  ): Promise<void> {
    const key = CacheKeyRegistry.getKey("ai_chat", "context", userId);
    const ttlConfig = CacheKeyRegistry.getTTL("ai_chat", "context");
    const version = 1;

    const context: AIChatContext = {
      userId,
      skills,
      recentJobsViewed,
      currentStep,
    };

    await cacheInvalidationService.set(key, context, ttlConfig, version);
    logger.info({ userId }, "Updated Ask Tush AI compilation context cache");
  }

  /**
   * Mock database query for sessions index.
   */
  private async fetchChatIndexFromPostgres(userId: string | number): Promise<ChatSessionMeta[]> {
    await new Promise((resolve) => setTimeout(resolve, 100));
    return [
      {
        chatId: "session_abc",
        title: "Resume feedback for Meta role",
        createdAt: Math.floor(Date.now() / 1000) - 3600,
        updatedAt: Math.floor(Date.now() / 1000) - 1800,
      },
    ];
  }

  /**
   * Mock database query for message list.
   */
  private async fetchChatSessionFromPostgres(chatId: string): Promise<ChatMessage[]> {
    await new Promise((resolve) => setTimeout(resolve, 150));
    return [
      {
        id: "msg_1",
        role: "user",
        content: "Hi Tush, how can I improve my Resume summary?",
        timestamp: Math.floor(Date.now() / 1000) - 3600,
      },
      {
        id: "msg_2",
        role: "assistant",
        content: "Add concrete achievements and quantitative outcomes matching the backend description.",
        timestamp: Math.floor(Date.now() / 1000) - 3500,
      },
    ];
  }
}

export const aiChatCacheService = new AIChatCacheService();
export default aiChatCacheService;
