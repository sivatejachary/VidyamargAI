"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import io, { Socket } from "socket.io-client";
import { create } from "zustand";
import offlineSyncManager from "../services/offline";

// Zustand store for managing warmup tier completions (for skeleton loading control)
interface WarmupState {
  tier1Complete: boolean;
  tier2Complete: boolean;
  tier3Complete: boolean;
  setTierComplete: (tier: number, complete: boolean) => void;
  resetWarmup: () => void;
}

export const useWarmupStore = create<WarmupState>((set) => ({
  tier1Complete: false,
  tier2Complete: false,
  tier3Complete: false,
  setTierComplete: (tier, complete) =>
    set((state) => {
      if (tier === 1) return { ...state, tier1Complete: complete };
      if (tier === 2) return { ...state, tier2Complete: complete };
      if (tier === 3) return { ...state, tier3Complete: complete };
      return state;
    }),
  resetWarmup: () => set({ tier1Complete: false, tier2Complete: false, tier3Complete: false }),
}));

let socketInstance: Socket | null = null;

/**
 * Socket.IO Singleton Client connection provider
 */
export const getSocket = (token: string): Socket => {
  if (!socketInstance) {
    const backendUrl = process.env.NEXT_PUBLIC_REDIS_WS_URL || "http://localhost:5001";
    socketInstance = io(backendUrl, {
      auth: { token },
      autoConnect: false,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });
  }
  return socketInstance;
};

export const useReactQuerySync = (userId: string | number, token: string) => {
  const queryClient = useQueryClient();
  const setTierComplete = useWarmupStore((state) => state.setTierComplete);

  useEffect(() => {
    if (!userId || !token) return;

    const socket = getSocket(token);
    if (!socket.connected) {
      socket.connect();
    }

    // --- 1. Warmup Tier Events (Transitions Skeleton Loaders to Active Views) ---
    socket.on("warmup:tier_complete", (payload: { tier: number }) => {
      console.info(`[Sync] Warmup Tier ${payload.tier} is complete`);
      setTierComplete(payload.tier, true);
      
      // Hydrate query caches from IndexedDB fallback if Redis pre-fetched it
      if (payload.tier === 1) {
        queryClient.invalidateQueries({ queryKey: ["profile", userId] });
        queryClient.invalidateQueries({ queryKey: ["resume", userId] });
      } else if (payload.tier === 2) {
        queryClient.invalidateQueries({ queryKey: ["lms", "progress", userId] });
      }
    });

    // --- 2. Resume Sync Event ---
    socket.on("resume:sync", (payload: { data: any; analysis: any }) => {
      console.info("[Sync] Resume data sync received");
      queryClient.setQueryData(["resume", userId], payload.data);
      queryClient.setQueryData(["resume", "ai_feedback", userId], payload.analysis);
      offlineSyncManager.cacheSet(`resume:data:${userId}`, payload.data);
      offlineSyncManager.cacheSet(`resume:ai_feedback:${userId}`, payload.analysis);
    });



    // --- 4. LMS Progress Tracker Sync Event ---
    socket.on("lms:progress:sync", (payload: { courseId: string; progress: number; completedLessons: string[] }) => {
      console.info(`[Sync] LMS progress sync received for course: ${payload.courseId}`);
      queryClient.setQueryData(["lms", "progress", userId, payload.courseId], payload);
      offlineSyncManager.cacheSet(`lms:progress:${userId}:${payload.courseId}`, payload);
    });

    // --- 5. LMS Certificates Sync Event ---
    socket.on("lms:certificate:sync", (payload: any) => {
      console.info("[Sync] New course certificate issued");
      queryClient.setQueryData(["lms", "certificate", userId, payload.courseId], payload);
      offlineSyncManager.cacheSet(`lms:certificate:${userId}:${payload.courseId}`, payload);
    });

    // --- 6. Real-time Messenger Sync Event ---
    socket.on("message:new", (payload: { chatId: string; message: any }) => {
      console.info(`[Sync] Message received in thread: ${payload.chatId}`);
      queryClient.setQueryData(
        ["chat", "session", userId, payload.chatId],
        (oldMessages: any[] | undefined) => {
          if (!oldMessages) return [payload.message];
          // Prevent double insertion
          if (oldMessages.some((m) => m.id === payload.message.id)) return oldMessages;
          return [...oldMessages, payload.message];
        }
      );
    });

    // --- 7. Real-time Theme Synchronization Event ---
    socket.on("theme:sync", (payload: { theme: string }) => {
      console.info(`[Sync] Theme sync event received: ${payload.theme}`);
      localStorage.setItem("theme", payload.theme);
      if (payload.theme === "light") {
        document.documentElement.classList.add("light-theme");
        document.documentElement.classList.remove("dark");
      } else {
        document.documentElement.classList.remove("light-theme");
        document.documentElement.classList.add("dark");
      }
    });

    return () => {
      socket.off("warmup:tier_complete");
      socket.off("resume:sync");

      socket.off("lms:progress:sync");
      socket.off("lms:certificate:sync");
      socket.off("message:new");
      socket.off("theme:sync");
    };
  }, [userId, token, queryClient, setTierComplete]);

  /**
   * Safe optimistic wrapper for executing data mutations.
   * Updates local React Query state immediately and schedules offline syncing if offline.
   */
  const executeOptimisticMutation = async <T = any>(
    queryKey: any[],
    mutationFn: () => Promise<T>,
    optimisticData: any,
    endpointUrl: string,
    method: "POST" | "PUT" | "DELETE" | "PATCH",
    module: string
  ): Promise<T | void> => {
    // 1. Cancel active outgoing queries
    await queryClient.cancelQueries({ queryKey });

    // 2. Snapshot current cache value for rollback
    const previousData = queryClient.getQueryData(queryKey);

    // 3. Optimistically set new data in React Query
    queryClient.setQueryData(queryKey, optimisticData);

    // 4. Check connectivity
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      console.warn("Client offline. Queueing mutation for later sync.");
      await offlineSyncManager.enqueueMutation(endpointUrl, method, optimisticData, module);
      return;
    }

    try {
      return await mutationFn();
    } catch (err) {
      console.error("Mutation failed. Rolling back optimistic state.", err);
      // Rollback to previous state on failure
      queryClient.setQueryData(queryKey, previousData);
      throw err;
    }
  };

  return { executeOptimisticMutation };
};
