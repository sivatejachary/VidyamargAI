import pg from "pg";
import { env } from "../config/env.js";

const { Pool } = pg;

const globalForPg = globalThis as unknown as {
  pgPool?: pg.Pool;
};

export const pool =
  globalForPg.pgPool ??
  new Pool({
    connectionString: env.DATABASE_URL,
    max: 3,
    idleTimeoutMillis: 10000,
    connectionTimeoutMillis: 5000,
  });

if (env.NODE_ENV !== "production") {
  globalForPg.pgPool = pool;
}

pool.on("connect", (client) => {
  client
    .query("SET search_path TO vidyamarg, public;")
    .catch((error) => {
      console.error("[Database] Failed to set search_path:", error);
    });
});

pool.on("error", (error) => {
  console.error("[Database Pool Error]", error);
});

export const query = async <T extends pg.QueryResultRow = pg.QueryResultRow>(
  text: string,
  params?: unknown[]
): Promise<pg.QueryResult<T>> => {
  const start = Date.now();
  try {
    const result = await pool.query<T>(text, params);
    const duration = Date.now() - start;
    if (duration > 200) {
      console.warn(`[Slow Query - ${duration}ms]: ${text.slice(0, 150)}`);
    }
    return result;
  } catch (error) {
    console.error(
      `[Database Query Error]: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
    throw error;
  }
};
