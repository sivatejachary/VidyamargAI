import { Router, Request, Response } from "express";
import multer from "multer";
import pdfParse from "pdf-parse";
import { query } from "../database/pool.js";
import { authenticateJwt } from "../middleware/auth.js";

export const profileRouter = Router();
const upload = multer({ limits: { fileSize: 5 * 1024 * 1024 } });

profileRouter.get("/candidates/profile", authenticateJwt, async (req: Request, res: Response) => {
  const user = req.user!;
  let candRes = await query("SELECT * FROM candidates WHERE user_id = $1", [user.id]);
  let candidate = candRes.rows[0];

  if (!candidate) {
    const newCand = await query(
      `INSERT INTO candidates (user_id, status, current_step, created_at, updated_at)
       VALUES ($1, 'Registered', 'Profile', NOW(), NOW())
       RETURNING *`,
      [user.id]
    );
    candidate = newCand.rows[0];
  }

  const profRes = await query(
    `SELECT experience_years, skills_graph FROM candidate_profiles 
     WHERE candidate_id = $1 ORDER BY created_at DESC LIMIT 1`,
    [candidate.id]
  );
  const profile = profRes.rows[0];

  res.json({
    ...candidate,
    user: { id: user.id, email: user.email, full_name: user.full_name, role: user.role },
    experience_years: profile?.experience_years || 0,
  });
});

profileRouter.put("/candidates/profile", authenticateJwt, async (req: Request, res: Response) => {
  const user = req.user!;
  const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
  const candidate = candRes.rows[0];

  const { parsed_name, parsed_phone, current_step } = req.body;

  if (candidate) {
    await query(
      `UPDATE candidates 
       SET parsed_phone = COALESCE($1, parsed_phone),
           current_step = COALESCE($2, current_step),
           status = 'Profile Completed',
           updated_at = NOW()
       WHERE id = $3`,
      [parsed_phone, current_step, candidate.id]
    );

    if (parsed_name) {
      await query("UPDATE users SET full_name = $1 WHERE id = $2", [parsed_name, user.id]);
    }
  }

  res.json({ message: "Profile updated successfully" });
});

profileRouter.post("/candidates/resume", authenticateJwt, upload.single("file"), async (req: Request, res: Response) => {
  if (!req.file) {
    res.status(400).json({ detail: "No file uploaded" });
    return;
  }

  const user = req.user!;
  const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
  const candidate = candRes.rows[0];

  if (!candidate) {
    res.status(404).json({ detail: "Candidate profile not found" });
    return;
  }

  let extractedText = "";
  try {
    const pdfData = await pdfParse(req.file.buffer);
    extractedText = pdfData.text;
  } catch (e) {
    console.warn("Could not parse PDF buffer, storing raw file reference:", e);
  }

  const resumeUrl = `https://storage.vidyamargai.app/resumes/candidate_${candidate.id}_${Date.now()}.pdf`;

  const resumeRes = await query(
    `INSERT INTO candidate_resumes (candidate_id, resume_url, original_filename, parsed_text, uploaded_at)
     VALUES ($1, $2, $3, $4, NOW())
     RETURNING id, resume_url, uploaded_at`,
    [candidate.id, resumeUrl, req.file.originalname, extractedText]
  );

  res.json({
    message: "Resume uploaded successfully. Profile analysis is running in the background.",
    url: resumeRes.rows[0].resume_url,
  });
});

profileRouter.get("/candidates/resume", authenticateJwt, async (req: Request, res: Response) => {
  const user = req.user!;
  const candRes = await query("SELECT id FROM candidates WHERE user_id = $1", [user.id]);
  if (!candRes.rows[0]) {
    res.status(404).json({ detail: "Candidate not found" });
    return;
  }

  const resumeRes = await query(
    `SELECT id, resume_url, uploaded_at FROM candidate_resumes 
     WHERE candidate_id = $1 ORDER BY uploaded_at DESC LIMIT 1`,
    [candRes.rows[0].id]
  );

  if (!resumeRes.rows[0]) {
    res.status(404).json({ detail: "No resume found" });
    return;
  }

  res.json(resumeRes.rows[0]);
});
