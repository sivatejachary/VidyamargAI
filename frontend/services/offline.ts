"use client";

export interface OfflineMutation {
  id?: number;
  url: string;
  method: "POST" | "PUT" | "DELETE" | "PATCH";
  body: string; // JSON string
  timestamp: number;
  module: string;
}

export interface LocalCacheEntry {
  key: string;
  value: any;
  timestamp: number;
}

export class OfflineSyncManager {
  private dbName = "VidyamargAI_OfflineCache";
  private dbVersion = 1;
  private isSyncing = false;

  constructor() {
    if (typeof window !== "undefined") {
      this.registerOnlineListeners();
    }
  }

  /**
   * Opens/Initializes the IndexedDB local stores.
   */
  private openDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      if (typeof window === "undefined") {
        return reject(new Error("IndexedDB is only available in browser environments"));
      }

      const request = window.indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);

      request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
        const db = request.result;
        
        // 1. Store for caching GET responses
        if (!db.objectStoreNames.contains("cache")) {
          db.createObjectStore("cache", { keyPath: "key" });
        }

        // 2. Store for queuing write mutations when offline
        if (!db.objectStoreNames.contains("mutation_queue")) {
          db.createObjectStore("mutation_queue", { keyPath: "id", autoIncrement: true });
        }
      };
    });
  }

  /**
   * Caches a GET response in local IndexedDB.
   */
  public async cacheSet(key: string, value: any): Promise<void> {
    try {
      const db = await this.openDB();
      const transaction = db.transaction("cache", "readwrite");
      const store = transaction.objectStore("cache");
      
      const entry: LocalCacheEntry = {
        key,
        value,
        timestamp: Date.now(),
      };
      
      await new Promise<void>((resolve, reject) => {
        const req = store.put(entry);
        req.onsuccess = () => resolve();
        req.onerror = () => reject(req.error);
      });
    } catch (err) {
      console.error("IndexedDB cacheSet failed:", err);
    }
  }

  /**
   * Retrieves a cached GET response from IndexedDB.
   */
  public async cacheGet(key: string): Promise<any | null> {
    try {
      const db = await this.openDB();
      const transaction = db.transaction("cache", "readonly");
      const store = transaction.objectStore("cache");
      
      const result = await new Promise<LocalCacheEntry | null>((resolve, reject) => {
        const req = store.get(key);
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => reject(req.error);
      });

      return result ? result.value : null;
    } catch (err) {
      console.error("IndexedDB cacheGet failed:", err);
      return null;
    }
  }

  /**
   * Enqueues a write mutation to the IndexedDB queue when offline.
   */
  public async enqueueMutation(
    url: string,
    method: OfflineMutation["method"],
    body: any,
    module: string
  ): Promise<void> {
    try {
      const db = await this.openDB();
      const transaction = db.transaction("mutation_queue", "readwrite");
      const store = transaction.objectStore("mutation_queue");

      const mutation: OfflineMutation = {
        url,
        method,
        body: JSON.stringify(body),
        timestamp: Date.now(),
        module,
      };

      await new Promise<void>((resolve, reject) => {
        const req = store.add(mutation);
        req.onsuccess = () => resolve();
        req.onerror = () => reject(req.error);
      });

      console.info(`Mutation enqueued offline for module: ${module}`);
      
      // If client is online, attempt immediate sync
      if (navigator.onLine) {
        this.syncOfflineMutations();
      }
    } catch (err) {
      console.error("Failed to enqueue offline mutation:", err);
    }
  }

  /**
   * Replays and syncs all pending offline mutations to the backend server.
   * Incorporates Last-Write-Wins (LWW) conflict resolution logic.
   */
  public async syncOfflineMutations(): Promise<void> {
    if (this.isSyncing) return;
    this.isSyncing = true;

    try {
      const db = await this.openDB();
      const transaction = db.transaction("mutation_queue", "readwrite");
      const store = transaction.objectStore("mutation_queue");

      // Fetch all queued mutations
      const mutations = await new Promise<OfflineMutation[]>((resolve, reject) => {
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      });

      if (mutations.length === 0) {
        this.isSyncing = false;
        return;
      }

      console.info(`Found ${mutations.length} pending mutations to sync. Executing conflict resolution...`);

      // Conflict Resolution: Last-Write-Wins (LWW)
      // Deduplicate mutations targeting same URL/module entity, retaining only the latest.
      const resolvedMutationsMap = new Map<string, OfflineMutation>();
      
      mutations.forEach((mut) => {
        const dedupKey = `${mut.method}:${mut.url}`;
        const existing = resolvedMutationsMap.get(dedupKey);
        
        if (!existing || existing.timestamp < mut.timestamp) {
          resolvedMutationsMap.set(dedupKey, mut);
        }
      });

      const processedMutations = Array.from(resolvedMutationsMap.values()).sort(
        (a, b) => a.timestamp - b.timestamp
      );

      // Sequentially replay deduped mutations
      for (const mutation of processedMutations) {
        try {
          const headers: HeadersInit = {
            "Content-Type": "application/json",
          };
          
          if (typeof window !== "undefined") {
            const token = localStorage.getItem("auth_token");
            if (token) {
              headers["Authorization"] = `Bearer ${token}`;
            }
          }

          const response = await fetch(mutation.url, {
            method: mutation.method,
            headers,
            body: mutation.body,
          });

          if (!response.ok) {
            throw new Error(`Server returned status: ${response.status}`);
          }
          console.info(`Successfully synchronized mutation: ${mutation.method} ${mutation.url}`);
        } catch (serverErr) {
          console.error(`Failed to sync mutation ID ${mutation.id}:`, serverErr);
          // Keep failing mutations in queue to retry on next connection
          this.isSyncing = false;
          return;
        }
      }

      // Clear sync queue on complete success
      const clearTx = db.transaction("mutation_queue", "readwrite");
      const clearStore = clearTx.objectStore("mutation_queue");
      await new Promise<void>((resolve, reject) => {
        const req = clearStore.clear();
        req.onsuccess = () => resolve();
        req.onerror = () => reject(req.error);
      });

      console.info("Offline sync queue cleared successfully");
    } catch (err) {
      console.error("Error running offline sync pipeline:", err);
    } finally {
      this.isSyncing = false;
    }
  }

  /**
   * Attaches window event listeners for online connectivity triggers.
   */
  private registerOnlineListeners(): void {
    window.addEventListener("online", () => {
      console.info("Device re-established network connection. Triggering offline sync.");
      this.syncOfflineMutations();
    });

    window.addEventListener("offline", () => {
      console.warn("Device disconnected. Operating in offline caching mode.");
    });
  }
}

export const offlineSyncManager = new OfflineSyncManager();
export default offlineSyncManager;
