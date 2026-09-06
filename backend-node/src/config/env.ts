import dotenv from "dotenv";
import { z } from "zod";

dotenv.config();

const envSchema = z.object({
  PORT: z.coerce.number().default(8000),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  DATABASE_URL: z.string().default(
    "postgresql://postgres:CDVByqTUKjxAlWjBkyOIjXTAlcAaakUf@hayabusa.proxy.rlwy.net:42919/railway"
  ),
  REDIS_URL: z.string().default(
    "redis://default:RzSjHlUiNuxBTUnuYrgCjORDjOivNFqk@thomas.proxy.rlwy.net:32069"
  ),
  JWT_SECRET: z.string().default("vidyamarg-ai-secret-key-production-fallback-2026"),
  JWT_EXPIRES_IN: z.string().default("15m"),
  INTEGRATION_SECRET: z.string().default("nirvahai-shared-integration-secret-2026"),
  ADMIN_REGISTRATION_KEY: z.string().default("VM_ADMIN_2026"),
  CORS_ORIGINS: z.string().default(
    "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,https://vidyamarg-ai.vercel.app"
  ),
  GROQ_API_KEY: z.string().optional().default(""),
  OPENAI_API_KEY: z.string().optional().default(""),
  RESEND_API_KEY: z.string().optional().default(""),
  SMTP_FROM_EMAIL: z.string().default("noreply@vidyamargai.com"),
});

export const env = envSchema.parse(process.env);
