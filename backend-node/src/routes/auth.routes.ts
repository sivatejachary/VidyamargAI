import { Router, Request, Response } from "express";
import bcrypt from "bcryptjs";
import * as jose from "jose";
import crypto from "crypto";
import { z } from "zod";
import { env } from "../config/env.js";
import { query } from "../database/pool.js";
import { authenticateJwt } from "../middleware/auth.js";
import { sendOtpEmail } from "../services/emailService.js";

export const authRouter = Router();

const signupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  full_name: z.string().min(1),
  role: z.string().optional().default("candidate"),
  security_key: z.string().optional(),
});

authRouter.post("/signup", async (req: Request, res: Response) => {
  const parseResult = signupSchema.safeParse(req.body);
  if (!parseResult.success) {
    res.status(400).json({ detail: parseResult.error.errors[0]?.message || "Invalid input data" });
    return;
  }

  const { email, password, full_name, role, security_key } = parseResult.data;
  const normalizedRole = role.toLowerCase().trim();

  if (["admin", "super_admin"].includes(normalizedRole)) {
    if (security_key !== env.ADMIN_REGISTRATION_KEY) {
      res.status(403).json({ detail: "Invalid Administrative Security Key. Access blocked." });
      return;
    }
  }

  const existing = await query("SELECT id FROM users WHERE email = $1", [email]);
  if (existing.rows.length > 0) {
    res.status(400).json({ detail: "Email already registered" });
    return;
  }

  const passwordHash = await bcrypt.hash(password, 12);
  const userResult = await query(
    `INSERT INTO users (email, password_hash, full_name, role, created_at, updated_at)
     VALUES ($1, $2, $3, $4, NOW(), NOW())
     RETURNING id, email, full_name, role, created_at`,
    [email, passwordHash, full_name, normalizedRole]
  );
  const user = userResult.rows[0];

  if (user.role === "candidate") {
    await query(
      `INSERT INTO candidates (user_id, status, current_step, created_at, updated_at)
       VALUES ($1, 'Registered', 'Profile', NOW(), NOW())`,
      [user.id]
    );
  }

  res.status(201).json(user);
});

authRouter.post("/login", async (req: Request, res: Response) => {
  const email = req.body.username || req.body.email;
  const password = req.body.password;

  if (!email || !password) {
    res.status(400).json({ detail: "Username and password are required" });
    return;
  }

  const userRes = await query(
    "SELECT id, email, password_hash, full_name, role FROM users WHERE email = $1",
    [email]
  );
  const user = userRes.rows[0];

  if (!user || !(await bcrypt.compare(password, user.password_hash))) {
    res.status(401).json({ detail: "Incorrect email or password" });
    return;
  }

  const secret = new TextEncoder().encode(env.JWT_SECRET);
  const accessToken = await new jose.SignJWT({ sub: user.email, role: user.role })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("15m")
    .sign(secret);

  const rawRefreshToken = crypto.randomBytes(32).toString("hex");
  const tokenHash = crypto.createHash("sha256").update(rawRefreshToken).digest("hex");
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

  await query(
    `INSERT INTO user_refresh_tokens (user_id, token_hash, expires_at, created_at)
     VALUES ($1, $2, $3, NOW())`,
    [user.id, tokenHash, expiresAt]
  );

  res.json({
    access_token: accessToken,
    token_type: "bearer",
    role: user.role,
    full_name: user.full_name,
    email: user.email,
    refresh_token: rawRefreshToken,
  });
});

authRouter.post("/refresh", async (req: Request, res: Response) => {
  const { refresh_token } = req.body;
  if (!refresh_token) {
    res.status(400).json({ detail: "Refresh token is required" });
    return;
  }

  const tokenHash = crypto.createHash("sha256").update(refresh_token).digest("hex");
  const tokenRes = await query(
    `SELECT user_id, expires_at FROM user_refresh_tokens 
     WHERE token_hash = $1 AND expires_at > NOW()`,
    [tokenHash]
  );
  const tokenRow = tokenRes.rows[0];

  if (!tokenRow) {
    res.status(401).json({ detail: "Invalid or expired refresh token" });
    return;
  }

  const userRes = await query("SELECT email, role FROM users WHERE id = $1", [tokenRow.user_id]);
  const user = userRes.rows[0];

  const secret = new TextEncoder().encode(env.JWT_SECRET);
  const accessToken = await new jose.SignJWT({ sub: user.email, role: user.role })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("15m")
    .sign(secret);

  res.json({ access_token: accessToken, token_type: "bearer" });
});

authRouter.post("/logout", async (req: Request, res: Response) => {
  const { refresh_token } = req.body;
  if (refresh_token) {
    const tokenHash = crypto.createHash("sha256").update(refresh_token).digest("hex");
    await query("DELETE FROM user_refresh_tokens WHERE token_hash = $1", [tokenHash]);
  }
  res.json({ message: "Successfully logged out" });
});

authRouter.get("/me", authenticateJwt, (req: Request, res: Response) => {
  res.json(req.user);
});

authRouter.post("/forgot-password", async (req: Request, res: Response) => {
  const { email } = req.body;
  if (!email) {
    res.status(400).json({ detail: "Email is required" });
    return;
  }

  const userRes = await query("SELECT id FROM users WHERE email = $1", [email]);
  if (userRes.rows.length === 0) {
    res.status(404).json({ detail: "Email not registered" });
    return;
  }

  const recentOtpRes = await query(
    `SELECT COUNT(*) FROM otps 
     WHERE email = $1 AND created_at >= NOW() - INTERVAL '15 minutes'`,
    [email]
  );
  if (parseInt(recentOtpRes.rows[0].count, 10) >= 3) {
    res.status(429).json({ detail: "Rate limit exceeded. Max 3 requests per 15 minutes." });
    return;
  }

  const code = Math.floor(100000 + Math.random() * 900000).toString();
  const expiry = new Date(Date.now() + 10 * 60 * 1000);

  await query(
    `INSERT INTO otps (email, otp, expiry_time, used, created_at)
     VALUES ($1, $2, $3, false, NOW())`,
    [email, code, expiry]
  );

  await sendOtpEmail(email, code);
  res.json({ message: "A verification code has been sent to your registered email address." });
});

authRouter.post("/reset-password", async (req: Request, res: Response) => {
  const { email, code, new_password } = req.body;
  if (!email || !code || !new_password) {
    res.status(400).json({ detail: "Missing email, code, or new_password" });
    return;
  }

  const otpRes = await query(
    `SELECT id FROM otps 
     WHERE email = $1 AND otp = $2 AND used = false AND expiry_time > NOW()`,
    [email, code]
  );
  if (otpRes.rows.length === 0) {
    res.status(400).json({ detail: "Invalid or expired verification code" });
    return;
  }

  const passwordHash = await bcrypt.hash(new_password, 12);
  await query("UPDATE users SET password_hash = $1 WHERE email = $2", [passwordHash, email]);
  await query("UPDATE otps SET used = true WHERE id = $1", [otpRes.rows[0].id]);

  res.json({ message: "Password updated successfully" });
});
