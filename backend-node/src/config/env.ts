import dotenv from "dotenv";
import { z } from "zod";

dotenv.config();

const envSchema = z.object({
  PORT: z.coerce.number().default(8000),
  NODE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),
  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),
  REDIS_URL: z.string().min(1, "REDIS_URL is required"),
  JWT_SECRET: z.string().min(16, "JWT_SECRET must be at least 16 characters"),
  JWT_EXPIRES_IN: z.string().default("15m"),
  INTEGRATION_SECRET: z.string().min(8, "INTEGRATION_SECRET must be at least 8 characters"),
  ADMIN_REGISTRATION_KEY: z.string().min(6, "ADMIN_REGISTRATION_KEY must be at least 6 characters"),
  CORS_ORIGINS: z.string().default(
    "http://localhost:3000,http://localhost:5000,https://vidyamarg-ai.vercel.app"
  ),
  GROQ_API_KEY: z.string().optional().default(""),
  OPENAI_API_KEY: z.string().optional().default(""),
  RESEND_API_KEY: z.string().optional().default(""),
  SMTP_FROM_EMAIL: z
    .string()
    .email()
    .default("noreply@vidyamargai.com"),
});

export const env = envSchema.parse(process.env);
