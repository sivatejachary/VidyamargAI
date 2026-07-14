"use client";

import { useState, useEffect, FormEvent } from "react";

interface Job {
  id: string;
  title: string;
  description: string;
  requirements: string[];
  status: string;
  employment_type?: string;
  location_type?: string;
  salary_min?: number;
  salary_max?: number;
  currency?: string;
  created_at: string;
  department_id?: string;
}

const HR_AGENT_URL = process.env.NEXT_PUBLIC_HR_AGENT_URL || "http://localhost:3000";
const TENANT_SLUG = process.env.NEXT_PUBLIC_HR_TENANT_SLUG || "dev-tenant";

// â”€â”€â”€ Apply Modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function ApplyModal({ job, onClose }: { job: Job; onClose: () => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleApply = async (e: FormEvent) => {
    e.preventDefault();
    if (!consent) { setError("Please accept data processing consent."); return; }
    if (!resumeText.trim()) { setError("Please paste your resume text."); return; }
    setLoading(true);
    setError("");
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const base = apiBase.replace(/\/api\/v1\/?$/, "");

      const res = await fetch(`${base}/api/v1/public/applications`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Tenant-Slug": TENANT_SLUG },
        body: JSON.stringify({
          job_id: job.id,
          candidate_name: name.trim(),
          candidate_email: email.trim(),
          resume_text: resumeText.trim(),
          resume_url: `https://vidyamargai.app/resumes/${encodeURIComponent(name.replace(" ", "_"))}.pdf`,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess(true);
      } else {
        setError(data.detail || "Application failed. Please try again.");
      }
    } catch {
      setError("Cannot connect to server. Make sure HR Agent backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 9999,
        background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 20,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: "linear-gradient(135deg, #1e1b4b, #1a1a2e)",
        border: "1px solid rgba(139,92,246,0.3)", borderRadius: 20,
        width: "100%", maxWidth: 560, maxHeight: "90vh", overflowY: "auto",
        padding: 32,
      }}>
        {success ? (
          <div style={{ textAlign: "center", padding: "32px 0" }}>
            <div style={{ fontSize: 56, marginBottom: 16 }}>ðŸŽ‰</div>
            <h2 style={{ color: "#a78bfa", fontWeight: 800, marginBottom: 12 }}>Application Submitted!</h2>
            <p style={{ color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
              Your application for <strong style={{ color: "#c4b5fd" }}>{job.title}</strong> has been received.<br />
              The AI pipeline at HR Agent will now process your profile.
            </p>
            <div style={{ marginTop: 24, padding: 16, background: "rgba(139,92,246,0.1)", borderRadius: 12, textAlign: "left" }}>
              <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, margin: 0 }}>Track your application status at:</p>
              <a href={`${HR_AGENT_URL}/dashboard/candidates`} target="_blank" rel="noopener noreferrer"
                style={{ color: "#a78bfa", fontSize: 13, fontWeight: 600 }}>
                {HR_AGENT_URL}/dashboard/candidates â†’
              </a>
            </div>
            <button onClick={onClose} style={{
              marginTop: 20, padding: "12px 32px", background: "linear-gradient(135deg,#7c3aed,#6366f1)",
              border: "none", borderRadius: 10, color: "#fff", fontWeight: 700, cursor: "pointer", fontSize: 15,
            }}>
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleApply}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <div>
                <h2 style={{ color: "#fff", fontWeight: 800, margin: 0, fontSize: 20 }}>Apply Now</h2>
                <p style={{ color: "#a78bfa", margin: "4px 0 0", fontSize: 13 }}>{job.title}</p>
              </div>
              <button type="button" onClick={onClose} style={{
                background: "rgba(255,255,255,0.1)", border: "none", borderRadius: 8,
                color: "#fff", cursor: "pointer", fontSize: 18, width: 36, height: 36,
              }}>âœ•</button>
            </div>

            {error && (
              <div style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.4)", borderRadius: 10, padding: "10px 14px", marginBottom: 16, color: "#fca5a5", fontSize: 13 }}>
                {error}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
              {[
                { label: "Full Name *", value: name, set: setName, placeholder: "Alex Johnson", type: "text" },
                { label: "Email Address *", value: email, set: setEmail, placeholder: "alex@example.com", type: "email" },
              ].map(f => (
                <div key={f.label}>
                  <label style={{ display: "block", fontSize: 11, fontWeight: 700, marginBottom: 5, color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{f.label}</label>
                  <input
                    type={f.type} required value={f.value} onChange={e => f.set(e.target.value)} placeholder={f.placeholder}
                    style={{ width: "100%", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 10, padding: "10px 12px", color: "#f3f4f6", fontSize: 14, outline: "none", boxSizing: "border-box" }}
                  />
                </div>
              ))}
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, marginBottom: 5, color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Resume / CV (paste text) *</label>
              <textarea
                required value={resumeText} onChange={e => setResumeText(e.target.value)}
                placeholder="Paste your resume here â€” skills, experience, education, achievements. AI will score it against the role."
                rows={7}
                style={{ width: "100%", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 10, padding: "10px 12px", color: "#f3f4f6", fontSize: 13, lineHeight: 1.6, resize: "vertical", boxSizing: "border-box", fontFamily: "inherit", outline: "none" }}
              />
            </div>

            <div style={{ background: "rgba(139,92,246,0.1)", border: "1px solid rgba(139,92,246,0.25)", borderRadius: 10, padding: 14, marginBottom: 20 }}>
              <label style={{ display: "flex", gap: 10, cursor: "pointer", alignItems: "flex-start" }}>
                <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}
                  style={{ width: 16, height: 16, marginTop: 2, flexShrink: 0, accentColor: "#7c3aed" }} />
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", lineHeight: 1.6 }}>
                  I consent to my personal data being processed for recruitment purposes under GDPR by <strong style={{ color: "#a78bfa" }}>{TENANT_SLUG}</strong>. Data deleted after 90 days if unsuccessful.
                </span>
              </label>
            </div>

            <button type="submit" disabled={loading || !consent} style={{
              width: "100%", padding: "14px 24px",
              background: loading || !consent ? "rgba(124,58,237,0.3)" : "linear-gradient(135deg,#7c3aed,#6366f1)",
              border: "none", borderRadius: 12, color: "#fff", fontWeight: 800, fontSize: 15,
              cursor: loading || !consent ? "not-allowed" : "pointer", transition: "all 0.2s",
            }}>
              {loading ? "Submitting to AI Pipeline..." : "Submit Application ðŸš€"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

// â”€â”€â”€ Main Jobs Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function CandidateJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [applyingJob, setApplyingJob] = useState<Job | null>(null);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const base = apiBase.replace(/\/api\/v1\/?$/, "");

    fetch(`${base}/api/v1/public/jobs`, {
      headers: { "X-Tenant-Slug": TENANT_SLUG },
    })
      .then(r => r.ok ? r.json() : [])
      .then((data: Job[]) => setJobs(data))
      .catch(() => setError("Could not load jobs. Make sure HR Agent backend is running at localhost:8000."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = jobs.filter(j => {
    const matchSearch = j.title.toLowerCase().includes(search.toLowerCase()) ||
      j.description?.toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter === "ALL" || j.location_type === typeFilter || j.employment_type === typeFilter;
    return matchSearch && matchType;
  });

  return (
    <div style={{ minHeight: "100vh", background: "#0f0a1e", color: "#f3f4f6", fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* Header */}
      <div style={{
        background: "rgba(139,92,246,0.08)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(139,92,246,0.2)", padding: "16px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, zIndex: 50,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 24 }}>ðŸŽ¯</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16 }}>VidyaMarg AI â€” Job Board</div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.45)" }}>Live openings from HR Agent Â· Powered by AI</div>
          </div>
        </div>
        <a href={HR_AGENT_URL} target="_blank" rel="noopener noreferrer" style={{
          padding: "8px 16px", background: "rgba(99,102,241,0.2)", border: "1px solid rgba(99,102,241,0.4)",
          borderRadius: 8, color: "#a5b4fc", fontSize: 12, fontWeight: 700, textDecoration: "none",
          display: "flex", alignItems: "center", gap: 6,
        }}>
          HR Agent Dashboard â†’
        </a>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 20px" }}>
        {/* Hero */}
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 16px",
            background: "rgba(139,92,246,0.15)", border: "1px solid rgba(139,92,246,0.3)",
            borderRadius: 20, color: "#c4b5fd", fontSize: 12, fontWeight: 700,
            marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.08em",
          }}>
            ðŸ¤– AI-Powered Hiring Â· Live from HR Agent
          </div>
          <h1 style={{ fontSize: 42, fontWeight: 900, margin: "0 0 12px", background: "linear-gradient(135deg,#c4b5fd,#818cf8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Find Your Dream Job
          </h1>
          <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 16, maxWidth: 500, margin: "0 auto" }}>
            Apply in seconds. AI analyzes your profile and connects you with the right opportunity.
          </p>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: 12, marginBottom: 32, flexWrap: "wrap" }}>
          <input
            type="text" placeholder="Search jobs, skills, titles..." value={search} onChange={e => setSearch(e.target.value)}
            style={{
              flex: 1, minWidth: 280, padding: "12px 16px",
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 12, color: "#f3f4f6", fontSize: 14, outline: "none", fontFamily: "inherit",
            }}
          />
          {["ALL", "REMOTE", "HYBRID", "ON_SITE", "FULL_TIME", "PART_TIME"].map(f => (
            <button key={f} onClick={() => setTypeFilter(f)} style={{
              padding: "10px 16px", borderRadius: 10, fontWeight: 700, fontSize: 12, cursor: "pointer",
              background: typeFilter === f ? "rgba(139,92,246,0.4)" : "rgba(255,255,255,0.06)",
              border: typeFilter === f ? "1px solid rgba(139,92,246,0.6)" : "1px solid rgba(255,255,255,0.1)",
              color: typeFilter === f ? "#c4b5fd" : "rgba(255,255,255,0.6)",
              textTransform: "uppercase", letterSpacing: "0.05em",
            }}>{f.replace("_", " ")}</button>
          ))}
        </div>

        {/* Results count */}
        <div style={{ marginBottom: 20, color: "rgba(255,255,255,0.4)", fontSize: 13 }}>
          {loading ? "Loading jobs from HR Agent..." : `${filtered.length} open position${filtered.length !== 1 ? "s" : ""} found`}
        </div>

        {/* Error */}
        {error && (
          <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 12, padding: 16, marginBottom: 24, color: "#fca5a5", fontSize: 14 }}>
            âš ï¸ {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {[1, 2, 3].map(i => (
              <div key={i} style={{ background: "rgba(255,255,255,0.04)", borderRadius: 16, padding: 24, animation: "pulse 1.5s infinite" }}>
                <div style={{ height: 20, background: "rgba(255,255,255,0.06)", borderRadius: 8, marginBottom: 12, width: "40%" }} />
                <div style={{ height: 14, background: "rgba(255,255,255,0.04)", borderRadius: 6, width: "70%" }} />
              </div>
            ))}
          </div>
        )}

        {/* No jobs */}
        {!loading && filtered.length === 0 && !error && (
          <div style={{ textAlign: "center", padding: "80px 0", color: "rgba(255,255,255,0.4)" }}>
            <div style={{ fontSize: 56, marginBottom: 16 }}>ðŸ“­</div>
            <p style={{ fontWeight: 600, fontSize: 18, marginBottom: 8 }}>No jobs found</p>
            <p style={{ fontSize: 14 }}>
              {search ? "Try adjusting your search." : "HR Agent hasn't published any jobs yet. "}
              <a href={`${HR_AGENT_URL}/dashboard/jobs`} target="_blank" rel="noopener noreferrer" style={{ color: "#a78bfa" }}>
                Create a job in HR Agent â†’
              </a>
            </p>
          </div>
        )}

        {/* Job grid */}
        <div style={{ display: "grid", gridTemplateColumns: selectedJob ? "1fr 380px" : "1fr", gap: 20 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {filtered.map(job => (
              <div
                key={job.id}
                onClick={() => setSelectedJob(selectedJob?.id === job.id ? null : job)}
                style={{
                  background: selectedJob?.id === job.id
                    ? "linear-gradient(135deg,rgba(124,58,237,0.2),rgba(99,102,241,0.1))"
                    : "rgba(255,255,255,0.04)",
                  border: selectedJob?.id === job.id ? "1px solid rgba(124,58,237,0.4)" : "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 16, padding: 24, cursor: "pointer",
                  transition: "all 0.2s", position: "relative",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ fontWeight: 800, fontSize: 18, margin: "0 0 8px", color: "#fff" }}>{job.title}</h3>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                      {job.employment_type && (
                        <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", background: "rgba(99,102,241,0.2)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 20, color: "#a5b4fc" }}>
                          {job.employment_type}
                        </span>
                      )}
                      {job.location_type && (
                        <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)", borderRadius: 20, color: "#6ee7b7" }}>
                          {job.location_type}
                        </span>
                      )}
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.3)", borderRadius: 20, color: "#fbbf24" }}>
                        ðŸ¤– AI Screened
                      </span>
                    </div>
                    <p style={{ color: "rgba(255,255,255,0.55)", fontSize: 13, lineHeight: 1.6, margin: 0, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                      {job.description}
                    </p>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    {job.salary_min && (
                      <div style={{ fontWeight: 800, fontSize: 18, color: "#fbbf24", marginBottom: 4 }}>
                        ${job.salary_min.toLocaleString()}â€“${job.salary_max?.toLocaleString()}
                      </div>
                    )}
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)" }}>
                      {new Date(job.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>

                {/* Skills */}
                {job.requirements?.length > 0 && (
                  <div style={{ marginTop: 16, display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {job.requirements.slice(0, 5).map((r, i) => (
                      <span key={i} style={{ fontSize: 11, padding: "3px 10px", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20, color: "rgba(255,255,255,0.7)" }}>
                        {r}
                      </span>
                    ))}
                    {job.requirements.length > 5 && (
                      <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", padding: "3px 8px" }}>+{job.requirements.length - 5} more</span>
                    )}
                  </div>
                )}

                <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
                  <button
                    onClick={e => { e.stopPropagation(); setApplyingJob(job); }}
                    style={{
                      padding: "10px 24px", background: "linear-gradient(135deg,#7c3aed,#6366f1)",
                      border: "none", borderRadius: 10, color: "#fff", fontWeight: 800, fontSize: 13,
                      cursor: "pointer", transition: "all 0.2s",
                      boxShadow: "0 4px 16px rgba(124,58,237,0.35)",
                    }}
                  >
                    Apply Now ðŸš€
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Detail Panel */}
          {selectedJob && (
            <div style={{
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(139,92,246,0.25)",
              borderRadius: 16, padding: 24, alignSelf: "start", position: "sticky", top: 80,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                <h3 style={{ fontWeight: 800, margin: 0, fontSize: 16 }}>{selectedJob.title}</h3>
                <button onClick={() => setSelectedJob(null)} style={{ background: "rgba(255,255,255,0.1)", border: "none", borderRadius: 6, color: "#fff", cursor: "pointer", width: 28, height: 28 }}>âœ•</button>
              </div>
              <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, lineHeight: 1.7, whiteSpace: "pre-line", marginBottom: 20 }}>
                {selectedJob.description}
              </p>
              <div style={{ fontWeight: 700, fontSize: 12, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>Requirements</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
                {selectedJob.requirements?.map((r, i) => (
                  <span key={i} style={{ fontSize: 12, padding: "4px 12px", background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.25)", borderRadius: 20, color: "#c4b5fd" }}>{r}</span>
                ))}
              </div>
              <button
                onClick={() => setApplyingJob(selectedJob)}
                style={{
                  width: "100%", padding: "14px", background: "linear-gradient(135deg,#7c3aed,#6366f1)",
                  border: "none", borderRadius: 12, color: "#fff", fontWeight: 800, fontSize: 15,
                  cursor: "pointer",
                }}
              >
                Apply for this Role ðŸš€
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Apply Modal */}
      {applyingJob && <ApplyModal job={applyingJob} onClose={() => setApplyingJob(null)} />}
    </div>
  );
}
