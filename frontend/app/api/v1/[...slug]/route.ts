import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import * as jose from "jose";
import crypto from "crypto";
import { query } from "@/lib/db";

const JWT_SECRET = process.env.JWT_SECRET || "vidyamarg-ai-secret-key-production-fallback-2026";
const ADMIN_KEY = process.env.ADMIN_REGISTRATION_KEY || "VM_ADMIN_2026";
const INTEGRATION_SECRET = process.env.INTEGRATION_SECRET || "nirvahai-shared-integration-secret-2026";

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
  try {
    const { slug } = await params;
    const path = slug.join("/");

    if (path === "health") {
      return NextResponse.json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        service: "vidyamarg-node-api",
        version: "2.0.0",
      });
    }

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

      const resRes = await query(
        "SELECT * FROM candidate_resumes WHERE candidate_id = $1 ORDER BY created_at DESC LIMIT 1",
        [candRes.rows[0].id]
      );
      return NextResponse.json(resRes.rows[0] || null);
    }

    if (path === "job-agent/dashboard") {
      const user = await verifyAuth(req);
      if (!user) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
      const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
      const candidateId = candRes.rows[0]?.id;

      const appsRes = await query(
        "SELECT status, COUNT(*) as count FROM applications WHERE candidate_id = $1 GROUP BY status",
        [candidateId]
      );
      const summary: Record<string, number> = {};
      appsRes.rows.forEach((r: any) => {
        summary[r.status] = parseInt(r.count, 10);
      });

      return NextResponse.json({
        agent_status: "ACTIVE",
        match_quality_avg: 88.5,
        applications_summary: summary,
        metrics: {
          total_applied: summary["applied"] || 0,
          interviews_scheduled: summary["interview_scheduled"] || 0,
          offers_received: summary["offer_received"] || 0,
        },
      });
    }

    if (path === "job-agent/jobs") {
      const { searchParams } = new URL(req.url);
      const page = parseInt(searchParams.get("page") || "1", 10);
      const limit = 20;
      const offset = (page - 1) * limit;

      const jobsRes = await query(
        `SELECT id, title, company_name, location, location_type, salary_min, salary_max, 
                currency, description, requirements, skills, created_at, false as is_hr_job
         FROM jobs 
         WHERE lifecycle_status != 'archived' OR lifecycle_status IS NULL
         ORDER BY created_at DESC 
         LIMIT $1 OFFSET $2`,
        [limit, offset]
      );
      return NextResponse.json({ items: jobsRes.rows, page, limit, total: jobsRes.rows.length });
    }

    if (path === "job-agent/applications") {
      const user = await verifyAuth(req);
      if (!user) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
      const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
      const candidateId = candRes.rows[0]?.id;

      const appsRes = await query(
        `SELECT a.id, a.job_id, a.status, a.match_score, a.applied_at,
                j.title as job_title, j.company_name, j.location,
                c.full_name as candidate_name, u.email as candidate_email
         FROM applications a
         LEFT JOIN jobs j ON a.job_id = j.id
         LEFT JOIN candidates cd ON a.candidate_id = cd.id
         LEFT JOIN users u ON cd.user_id = u.id
         LEFT JOIN candidate_profiles c ON cd.id = c.candidate_id
         WHERE a.candidate_id = $1
         ORDER BY a.applied_at DESC LIMIT 50`,
        [candidateId]
      );
      return NextResponse.json(appsRes.rows);
    }

    return NextResponse.json({ detail: `Route GET /api/v1/${path} not found` }, { status: 404 });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Internal server error" }, { status: 500 });
  }
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ slug: string[] }> }) {
  try {
    const { slug } = await params;
    const path = slug.join("/");
    let body: any = {};
    try {
      body = await req.json();
    } catch {}

    if (path === "auth/login") {
      const { email, password } = body;
      if (!email || !password) return NextResponse.json({ detail: "Email and password required" }, { status: 400 });

      const res = await query("SELECT id, email, password_hash, full_name, role FROM users WHERE email = $1", [email]);
      const user = res.rows[0];
      if (!user || !(await bcrypt.compare(password, user.password_hash))) {
        return NextResponse.json({ detail: "Incorrect email or password" }, { status: 401 });
      }

      const secret = new TextEncoder().encode(JWT_SECRET);
      const token = await new jose.SignJWT({ sub: user.email, role: user.role, uid: user.id })
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("7d")
        .sign(secret);

      return NextResponse.json({
        access_token: token,
        token_type: "bearer",
        user: { id: user.id, email: user.email, full_name: user.full_name, role: user.role },
      });
    }

    if (path === "auth/signup") {
      const { email, password, full_name, role, security_key } = body;
      if (!email || !password || !full_name) {
        return NextResponse.json({ detail: "Missing required fields" }, { status: 400 });
      }

      const normalizedRole = (role || "candidate").toLowerCase().trim();
      if (["admin", "super_admin"].includes(normalizedRole) && security_key !== ADMIN_KEY) {
        return NextResponse.json({ detail: "Invalid administrative security key" }, { status: 403 });
      }

      const existing = await query("SELECT id FROM users WHERE email = $1", [email]);
      if (existing.rows.length > 0) {
        return NextResponse.json({ detail: "Email already registered" }, { status: 400 });
      }

      const passwordHash = await bcrypt.hash(password, 12);
      const userResult = await query(
        "INSERT INTO users (email, password_hash, full_name, role, created_at, updated_at) VALUES ($1, $2, $3, $4, NOW(), NOW()) RETURNING id, email, full_name, role",
        [email, passwordHash, full_name, normalizedRole]
      );
      const user = userResult.rows[0];

      if (user.role === "candidate") {
        await query("INSERT INTO candidates (user_id, status, current_step, created_at, updated_at) VALUES ($1, 'Registered', 'Profile', NOW(), NOW())", [user.id]);
      }

      const secret = new TextEncoder().encode(JWT_SECRET);
      const token = await new jose.SignJWT({ sub: user.email, role: user.role, uid: user.id })
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("7d")
        .sign(secret);

      return NextResponse.json({
        access_token: token,
        token_type: "bearer",
        user,
      });
    }

    if (path === "sync/jobs") {
      const { job_id, tenant_slug, action, title, description, company_name, location, salary_min, salary_max, currency } = body;
      if (action === "delete") {
        await query("DELETE FROM hr_synced_jobs WHERE hr_job_id = $1", [job_id]);
      } else {
        await query(
          `INSERT INTO hr_synced_jobs 
            (hr_job_id, tenant_slug, title, description, company_name, location, salary_min, salary_max, currency, synced_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
           ON CONFLICT (hr_job_id) DO UPDATE SET
             title = EXCLUDED.title, description = EXCLUDED.description, company_name = EXCLUDED.company_name, synced_at = NOW()`,
          [job_id, tenant_slug, title, description, company_name, location, salary_min, salary_max, currency]
        );
      }
      return NextResponse.json({ success: true });
    }

    if (path === "sync/applications") {
      const { hr_agent_application_id, candidate_email, job_id, job_title, status } = body;
      const userRes = await query("SELECT id FROM users WHERE email = $1", [candidate_email]);
      if (!userRes.rows[0]) return NextResponse.json({ detail: "Candidate not found" }, { status: 404 });

      const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [userRes.rows[0].id]);
      const candidateId = candRes.rows[0]?.id;

      await query(
        `INSERT INTO applications (candidate_id, job_id, status, applied_at, updated_at)
         VALUES ($1, $2, $3, NOW(), NOW())
         ON CONFLICT (candidate_id, job_id) DO UPDATE SET status = EXCLUDED.status, updated_at = NOW()`,
        [candidateId, job_id, status || "applied"]
      );

      return NextResponse.json({ success: true, hr_agent_application_id, status: status || "applied" });
    }

    return NextResponse.json({ detail: `Route POST /api/v1/${path} not found` }, { status: 404 });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Internal server error" }, { status: 500 });
  }
}

export async function PUT(req: NextRequest, { params }: { params: Promise<{ slug: string[] }> }) {
  try {
    const { slug } = await params;
    const path = slug.join("/");
    const body = await req.json();

    if (path === "candidates/profile") {
      const user = await verifyAuth(req);
      if (!user) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

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

    return NextResponse.json({ detail: `Route PUT /api/v1/${path} not found` }, { status: 404 });
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Internal server error" }, { status: 500 });
  }
}
