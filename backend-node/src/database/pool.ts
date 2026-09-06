import pg from "pg";
const { Pool } = pg;
import { env } from "../config/env.js";

export const pool = new Pool({
  connectionString: env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

pool.on("connect", (client) => {
  client.query("SET search_path TO vidyamarg, public;");
});

export const query = async <T extends pg.QueryResultRow = any>(
  text: string,
  params?: any[]
): Promise<pg.QueryResult<T>> => {
  const start = Date.now();
  try {
    const res = await pool.query<T>(text, params);
    const duration = Date.now() - start;
    if (duration > 200) {
      console.warn(`[Slow Query - ${duration}ms]: ${text.slice(0, 150)}`);
    }
    return res;
  } catch (error) {
    console.error(`[Database Query Error]: ${error instanceof Error ? error.message : String(error)}`, { text });
    throw error;
  }
};
