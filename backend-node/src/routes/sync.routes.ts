import { Router, Request, Response, NextFunction } from "express";
import crypto from "crypto";
import { env } from "../config/env.js";
import { query } from "../database/pool.js";

export const syncRouter = Router();

export const verifySyncSignature = (req: Request, res: Response, next: NextFunction): void => {
  const secret = env.INTEGRATION_SECRET;
  const signature = (req.headers["x-event-signature"] || req.headers["X-Event-Signature"]) as string;
  const integrationKey = (req.headers["x-integration-key"] || req.headers["X-Integration-Key"]) as string;

  if (req.method === "GET") {
    if (integrationKey === secret || signature === secret) {
      next();
      return;
    }
    res.status(401).json({ detail: "Invalid integration key for GET request." });
    return;
  }

  if (!signature) {
    res.status(401).json({ detail: "Missing X-Event-Signature header." });
    return;
  }

  const rawBody = (req as any).rawBody || JSON.stringify(req.body);
  const computed = crypto.createHmac("sha256", secret).update(rawBody).digest("hex");

  if (signature !== computed) {
    res.status(401).json({ detail: "Invalid event signature." });
    return;
  }

  next();
};

syncRouter.use(verifySyncSignature);

syncRouter.post("/sync/jobs", async (req: Request, res: Response) => {
  const { job_id, tenant_slug, action, title, description, company_name, location, salary_min, salary_max, currency } = req.body;

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

  res.json({ success: true });
});

syncRouter.post("/sync/applications", async (req: Request, res: Response) => {
  const { hr_agent_application_id, candidate_email, job_id, job_title, status } = req.body;

  await query(
    `INSERT INTO hr_synced_applications 
      (hr_application_id, candidate_email, hr_job_id, job_title, current_status, synced_at)
     VALUES ($1, $2, $3, $4, $5, NOW())
     ON CONFLICT (hr_application_id) DO UPDATE SET
       current_status = EXCLUDED.current_status, synced_at = NOW()`,
    [hr_agent_application_id, candidate_email, job_id, job_title, status || "APPLIED"]
  );

  res.json({ success: true });
});

syncRouter.get("/sync/stages/:candidate_email", async (req: Request, res: Response) => {
  const email = req.params.candidate_email;
  const stagesRes = await query(
    `SELECT a.hr_application_id, a.hr_job_id, a.job_title, a.current_status,
            s.stage_number, s.stage_name, s.status as stage_status, s.score, s.feedback
     FROM hr_synced_applications a
     LEFT JOIN hr_application_stages s ON s.hr_application_id = a.hr_application_id
     WHERE a.candidate_email = $1
     ORDER BY a.hr_application_id, s.stage_number`,
    [email]
  );

  res.json(stagesRes.rows);
});
