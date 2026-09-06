import pg from "pg";
const { Pool } = pg;

const databaseUrl =
  process.env.DATABASE_URL ||
  "postgresql://postgres:CDVByqTUKjxAlWjBkyOIjXTAlcAaakUf@hayabusa.proxy.rlwy.net:42919/railway";

// Singleton pool for Serverless Functions
let pool: pg.Pool;

declare global {
  var __dbPool: pg.Pool | undefined;
}

if (!global.__dbPool) {
  global.__dbPool = new Pool({
    connectionString: databaseUrl,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  });

  global.__dbPool.on("connect", (client) => {
    client.query("SET search_path TO vidyamarg, public;");
  });
}

pool = global.__dbPool;

export const query = async <T extends pg.QueryResultRow = any>(
  text: string,
  params?: any[]
): Promise<pg.QueryResult<T>> => {
  try {
    return await pool.query<T>(text, params);
  } catch (error) {
    console.error("[Database Query Error]:", error instanceof Error ? error.message : String(error));
    throw error;
  }
};

export { pool };
