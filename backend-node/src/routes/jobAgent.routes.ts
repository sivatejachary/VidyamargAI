import { Router, Request, Response } from "express";
import { query } from "../database/pool.js";
import { authenticateJwt } from "../middleware/auth.js";

export const jobAgentRouter = Router();

jobAgentRouter.get("/job-agent/dashboard", authenticateJwt, async (req: Request, res: Response) => {
  const user = req.user!;
  const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
  const candidateId = candRes.rows[0]?.id;

  const appsRes = await query(
    `SELECT status, COUNT(*) as count 
     FROM applications 
     WHERE candidate_id = $1 
     GROUP BY status`,
    [candidateId]
  );

  const applicationsSummary: Record<string, number> = {};
  appsRes.rows.forEach((row) => {
    applicationsSummary[row.status] = parseInt(row.count, 10);
  });

  res.json({
    agent_status: "ACTIVE",
    match_quality_avg: 88.5,
    applications_summary: applicationsSummary,
    metrics: {
      total_applied: applicationsSummary["applied"] || 0,
      interviews_scheduled: applicationsSummary["interview_scheduled"] || 0,
      offers_received: applicationsSummary["offer_received"] || 0,
    },
  });
});

jobAgentRouter.get("/job-agent/jobs", authenticateJwt, async (req: Request, res: Response) => {
  const page = parseInt(req.query.page as string, 10) || 1;
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

  res.json({
    items: jobsRes.rows,
    page,
    limit,
    total: jobsRes.rows.length,
  });
});

jobAgentRouter.get("/job-agent/applications", authenticateJwt, async (req: Request, res: Response) => {
  const user = req.user!;
  const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
  const candidateId = candRes.rows[0]?.id;

  if (!candidateId) {
    res.json([]);
    return;
  }

  const appsRes = await query(
    `SELECT a.id, a.job_id, a.status, a.applied_at, j.title as job_title, j.company_name
     FROM applications a
     JOIN jobs j ON a.job_id = j.id
     WHERE a.candidate_id = $1
     ORDER BY a.applied_at DESC`,
    [candidateId]
  );

  res.json(appsRes.rows);
});

jobAgentRouter.post("/job-agent/applications", authenticateJwt, async (req: Request, res: Response) => {
  const user = req.user!;
  const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
  const candidateId = candRes.rows[0]?.id;

  const { job_id, status = "applied" } = req.body;
  if (!job_id) {
    res.status(400).json({ detail: "job_id is required" });
    return;
  }

  const newApp = await query(
    `INSERT INTO applications (candidate_id, job_id, status, applied_at)
     VALUES ($1, $2, $3, NOW())
     RETURNING *`,
    [candidateId, job_id, status]
  );

  res.status(201).json(newApp.rows[0]);
});
