"use client";

import React, { useState } from "react";
import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => {
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          gcTime: 1000 * 60 * 60 * 24, // 24 hours
          staleTime: 1000 * 60 * 5, // 5 minutes default
          refetchOnWindowFocus: false,
        },
      },
    });

    // Configure custom staleTimes for specific query keys:
    // - courses/curriculum: 30m
    client.setQueryDefaults(["courses"], { staleTime: 1000 * 60 * 30 });
    client.setQueryDefaults(["curriculum"], { staleTime: 1000 * 60 * 30 });
    
    // - certificates: 10m
    client.setQueryDefaults(["certificates"], { staleTime: 1000 * 60 * 10 });
    
    // - notifications: 30s
    client.setQueryDefaults(["notifications"], { staleTime: 1000 * 30 });
    
    // - progress: 5s
    client.setQueryDefaults(["progress"], { staleTime: 1000 * 5 });

    return client;
  });

  const [persister] = useState(() =>
    createSyncStoragePersister({
      storage: typeof window !== "undefined" ? window.localStorage : undefined,
    })
  );

  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister }}
    >
      {children}
    </PersistQueryClientProvider>
  );
}
