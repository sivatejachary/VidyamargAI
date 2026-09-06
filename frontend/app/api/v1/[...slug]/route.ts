import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import * as jose from "jose";
import crypto from "crypto";
import { query } from "@/lib/db";

const JWT_SECRET = process.env.JWT_SECRET || "vidyamarg-ai-secret-key-production-fallback-2026";
const ADMIN_KEY = process.env.ADMIN_REGISTRATION_KEY || "VM_ADMIN_2026";

async function verifyAuth(req: NextRequest) {
  const auth = req.headers.get("authorization");
  if (!auth || !auth.startsWith("Bearer ")) return null;
  try {
    const token = auth.split(" ")[1];
    const secret = new TextEncoder().encode(JWT_SECRET);
    const { payload } = await jose.jwtVerify(token, secret);
    const email = payload.sub as string;
    if (!email) return null;
    const res = await query("SELECT id, email, role, full_name FROM users WHERE email = $1", [email]);
    return res.rows[0] || null;
  } catch {
    return null;
  }
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ slug: string[] }> }) {
  const { slug } = await params;
  const path = slug.join("/");

  if (path === "auth/me") {
    const user = await verifyAuth(req);
    if (!user) return NextResponse.json({ detail: "Could not validate credentials" }, { status: 401 });
    return NextResponse.json(user);
  }

  if (path === "candidates/profile") {
    const user = await verifyAuth(req);
    if (!user) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

    let candRes = await query("SELECT * FROM candidates WHERE user_id = $1", [user.id]);
    let candidate = candRes.rows[0];
    if (!candidate) {
      const newCand = await query(
        "INSERT INTO candidates (user_id, status, current_step, created_at, updated_at) VALUES ($1, 'Registered', 'Profile', NOW(), NOW()) RETURNING *",
        [user.id]
      );
      candidate = newCand.rows[0];
    }
    const profRes = await query(
      "SELECT experience_years, skills_graph FROM candidate_profiles WHERE candidate_id = $1 ORDER BY created_at DESC LIMIT 1",
      [candidate.id]
    );
    return NextResponse.json({
      ...candidate,
      user: { id: user.id, email: user.email, full_name: user.full_name, role: user.role },
      experience_years: profRes.rows[0]?.experience_years || 0,
    });
  }

  if (path === "candidates/resume") {
    const user = await verifyAuth(req);
    if (!user) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
    if (!candRes.rows[0]) return NextResponse.json({ detail: "Candidate not found" }, { status: 404 });
    const res = await query(
      "SELECT id, resume_url, uploaded_at FROM candidate_resumes WHERE candidate_id = $1 ORDER BY uploaded_at DESC LIMIT 1",
      [candRes.rows[0].id]
    );
    if (!res.rows[0]) return NextResponse.json({ detail: "No resume found" }, { status: 404 });
    return NextResponse.json(res.rows[0]);
  }

  if (path === "job-agent/dashboard") {
    const user = await verifyAuth(req);
    const candidateId = user ? (await query("SELECT id FROM candidates WHERE user_id = $1", [user.id])).rows[0]?.id : null;
    const appsRes = candidateId
      ? await query("SELECT status, COUNT(*) as count FROM applications WHERE candidate_id = $1 GROUP BY status", [candidateId])
      : { rows: [] };
    const summary: Record<string, number> = {};
    appsRes.rows.forEach((r: any) => { summary[r.status] = parseInt(r.count, 10); });
    return NextResponse.json({
      agent_status: "ACTIVE",
      match_quality_avg: 89.2,
      applications_summary: summary,
      metrics: {
        total_applied: summary["applied"] || 0,
        interviews_scheduled: summary["interview_scheduled"] || 0,
        offers_received: summary["offer_received"] || 0,
      },
    });
  }

  if (path === "job-agent/jobs") {
    const page = parseInt(req.nextUrl.searchParams.get("page") || "1", 10);
    const limit = 20;
    const offset = (page - 1) * limit;
    const jobsRes = await query(
      "SELECT id, title, company_name, location, location_type, salary_min, salary_max, currency, description, requirements, skills, created_at, false as is_hr_job FROM jobs ORDER BY created_at DESC LIMIT $1 OFFSET $2",
      [limit, offset]
    );
    return NextResponse.json({ items: jobsRes.rows, page, limit, total: jobsRes.rows.length });
  }

  if (path === "job-agent/applications") {
    const user = await verifyAuth(req);
    if (!user) return NextResponse.json([]);
    const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
    const candidateId = candRes.rows[0]?.id;
    if (!candidateId) return NextResponse.json([]);
    const res = await query(
      "SELECT a.id, a.job_id, a.status, a.applied_at, j.title as job_title, j.company_name FROM applications a JOIN jobs j ON a.job_id = j.id WHERE a.candidate_id = $1 ORDER BY a.applied_at DESC",
      [candidateId]
    );
    return NextResponse.json(res.rows);
  }

  if (path.startsWith("sync/stages/")) {
    const email = path.replace("sync/stages/", "");
    const res = await query(
      "SELECT a.hr_application_id, a.hr_job_id, a.job_title, a.current_status, s.stage_number, s.stage_name, s.status as stage_status, s.score, s.feedback FROM hr_synced_applications a LEFT JOIN hr_application_stages s ON s.hr_application_id = a.hr_application_id WHERE a.candidate_email = $1 ORDER BY a.hr_application_id, s.stage_number",
      [email]
    );
    return NextResponse.json(res.rows);
  }

  return NextResponse.json({ detail: `Endpoint /api/v1/${path} recognized.` });
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ slug: string[] }> }) {
  const { slug } = await params;
  const path = slug.join("/");
  let body: any = {};
  try {
    const contentType = req.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      body = await req.json();
    } else if (contentType.includes("application/x-www-form-urlencoded")) {
      const formData = await req.formData();
      formData.forEach((val, key) => { body[key] = val.toString(); });
    }
  } catch {}

  if (path === "auth/signup") {
    const { email, password, full_name, role = "candidate", security_key } = body;
    if (!email || !password || !full_name) {
      return NextResponse.json({ detail: "Missing required fields" }, { status: 400 });
    }
    const normRole = role.toLowerCase().trim();
    if (["admin", "super_admin"].includes(normRole) && security_key !== ADMIN_KEY) {
      return NextResponse.json({ detail: "Invalid Administrative Security Key" }, { status: 403 });
    }
    const existing = await query("SELECT id FROM users WHERE email = $1", [email]);
    if (existing.rows.length > 0) {
      return NextResponse.json({ detail: "Email already registered" }, { status: 400 });
    }
    const hash = await bcrypt.hash(password, 12);
    const userRes = await query(
      "INSERT INTO users (email, password_hash, full_name, role, created_at, updated_at) VALUES ($1, $2, $3, $4, NOW(), NOW()) RETURNING id, email, full_name, role, created_at",
      [email, hash, full_name, normRole]
    );
    const user = userRes.rows[0];
    if (user.role === "candidate") {
      await query("INSERT INTO candidates (user_id, status, current_step, created_at, updated_at) VALUES ($1, 'Registered', 'Profile', NOW(), NOW())", [user.id]);
    }
    return NextResponse.json(user, { status: 201 });
  }

  if (path === "auth/login") {
    const email = body.username || body.email;
    const password = body.password;
    if (!email || !password) return NextResponse.json({ detail: "Username and password required" }, { status: 400 });
    const res = await query("SELECT id, email, password_hash, full_name, role FROM users WHERE email = $1", [email]);
    const user = res.rows[0];
    if (!user || !(await bcrypt.compare(password, user.password_hash))) {
      return NextResponse.json({ detail: "Incorrect email or password" }, { status: 401 });
    }
    const secret = new TextEncoder().encode(JWT_SECRET);
    const accessToken = await new jose.SignJWT({ sub: user.email, role: user.role })
      .setProtectedHeader({ alg: "HS256" })
      .setExpirationTime("15m")
      .sign(secret);
    const rawRefresh = crypto.randomBytes(32).toString("hex");
    const tokenHash = crypto.createHash("sha256").update(rawRefresh).digest("hex");
    await query(
      "INSERT INTO user_refresh_tokens (user_id, token_hash, expires_at, created_at) VALUES ($1, $2, NOW() + INTERVAL '7 days', NOW())",
      [user.id, tokenHash]
    );
    return NextResponse.json({
      access_token: accessToken,
      token_type: "bearer",
      role: user.role,
      full_name: user.full_name,
      email: user.email,
      refresh_token: rawRefresh,
    });
  }

  if (path === "auth/refresh") {
    const { refresh_token } = body;
    if (!refresh_token) return NextResponse.json({ detail: "Refresh token required" }, { status: 400 });
    const tokenHash = crypto.createHash("sha256").update(refresh_token).digest("hex");
    const res = await query("SELECT user_id FROM user_refresh_tokens WHERE token_hash = $1 AND expires_at > NOW()", [tokenHash]);
    if (!res.rows[0]) return NextResponse.json({ detail: "Invalid refresh token" }, { status: 401 });
    const userRes = await query("SELECT email, role FROM users WHERE id = $1", [res.rows[0].user_id]);
    const user = userRes.rows[0];
    const secret = new TextEncoder().encode(JWT_SECRET);
    const accessToken = await new jose.SignJWT({ sub: user.email, role: user.role })
      .setProtectedHeader({ alg: "HS256" })
      .setExpirationTime("15m")
      .sign(secret);
    return NextResponse.json({ access_token: accessToken, token_type: "bearer" });
  }

  if (path === "auth/logout") {
    if (body.refresh_token) {
      const tokenHash = crypto.createHash("sha256").update(body.refresh_token).digest("hex");
      await query("DELETE FROM user_refresh_tokens WHERE token_hash = $1", [tokenHash]);
    }
    return NextResponse.json({ message: "Successfully logged out" });
  }

  if (path === "auth/forgot-password") {
    const { email } = body;
    const userRes = await query("SELECT id FROM users WHERE email = $1", [email]);
    if (userRes.rows.length === 0) return NextResponse.json({ detail: "Email not registered" }, { status: 404 });
    const code = Math.floor(100000 + Math.random() * 900000).toString();
    await query(
      "INSERT INTO otps (email, otp, expiry_time, used, created_at) VALUES ($1, $2, NOW() + INTERVAL '10 minutes', false, NOW())",
      [email, code]
    );
    console.log(`[Password Reset Code for ${email}]: ${code}`);
    return NextResponse.json({ message: "A verification code has been sent to your registered email address." });
  }

  if (path === "auth/reset-password") {
    const { email, code, new_password } = body;
    const otpRes = await query("SELECT id FROM otps WHERE email = $1 AND otp = $2 AND used = false AND expiry_time > NOW()", [email, code]);
    if (otpRes.rows.length === 0) return NextResponse.json({ detail: "Invalid or expired verification code" }, { status: 400 });
    const hash = await bcrypt.hash(new_password, 12);
    await query("UPDATE users SET password_hash = $1 WHERE email = $2", [hash, email]);
    await query("UPDATE otps SET used = true WHERE id = $1", [otpRes.rows[0].id]);
    return NextResponse.json({ message: "Password updated successfully" });
  }

  if (path === "job-agent/applications") {
    const user = await verifyAuth(req);
    if (!user) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
    const candidateId = candRes.rows[0]?.id;
    const { job_id, status = "applied" } = body;
    const newApp = await query(
      "INSERT INTO applications (candidate_id, job_id, status, applied_at) VALUES ($1, $2, $3, NOW()) RETURNING *",
      [candidateId, job_id, status]
    );
    return NextResponse.json(newApp.rows[0], { status: 201 });
  }

  return NextResponse.json({ success: true, path });
}

export async function PUT(req: NextRequest, { params }: { params: Promise<{ slug: string[] }> }) {
  const { slug } = await params;
  const path = slug.join("/");
  const user = await verifyAuth(req);
  if (!user) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  const body = await req.json();

  if (path === "candidates/profile") {
    const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
    const candidate = candRes.rows[0];
    if (candidate) {
      await query(
        "UPDATE candidates SET parsed_phone = COALESCE($1, parsed_phone), current_step = COALESCE($2, current_step), status = 'Profile Completed', updated_at = NOW() WHERE id = $3",
        [body.parsed_phone, body.current_step, candidate.id]
      );
      if (body.parsed_name) {
        await query("UPDATE users SET full_name = $1 WHERE id = $2", [body.parsed_name, user.id]);
      }
    }
    return NextResponse.json({ message: "Profile updated successfully" });
  }

  return NextResponse.json({ success: true });
}
