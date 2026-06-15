"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { Briefcase, PlusCircle, Trash, CheckCircle } from "lucide-react";

export default function AdminJobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);

  // Form states
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("");
  const [salaryRange, setSalaryRange] = useState("");
  const [location, setLocation] = useState("");
  const [department, setDepartment] = useState("");

  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const fetchJobs = async () => {
    try {
      const data = await apiService.getJobs();
      setJobs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await apiService.createJob({
        title,
        description,
        required_skills: requiredSkills,
        experience_level: experienceLevel,
        salary_range: salaryRange,
        location,
        department
      });
      setSuccess("Job created successfully!");
      setTitle("");
      setDescription("");
      setRequiredSkills("");
      setExperienceLevel("");
      setSalaryRange("");
      setLocation("");
      setDepartment("");
      setFormOpen(false);
      await fetchJobs();
    } catch (err: any) {
      setError(err.message || "Failed to create position.");
    }
  };

  const handleArchiveJob = async (id: number) => {
    if (!confirm("Are you sure you want to archive this job opening?")) return;
    try {
      await apiService.deleteJob(id);
      await fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 md:p-12 max-w-6xl mx-auto flex flex-col gap-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">Job Openings Management</h1>
          <p className="text-sm text-gray-400 mt-1">
            Create, audit, and archive job positions registered inside the HireAI operating system.
          </p>
        </div>
        
        <button
          onClick={() => setFormOpen(!formOpen)}
          className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 px-4 py-2.5 rounded-xl text-xs font-bold text-white transition-all shadow-md"
        >
          <PlusCircle size={14} />
          <span>{formOpen ? "View List" : "Create Position"}</span>
        </button>
      </div>

      {success && (
        <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-emerald-400 text-xs font-medium flex items-center gap-2">
          <CheckCircle size={16} />
          <span>{success}</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-red-950/30 border border-red-800/40 text-red-400 text-xs font-medium">
          {error}
        </div>
      )}

      {formOpen ? (
        <form onSubmit={handleCreateJob} className="glass-panel p-8 rounded-2xl border border-gray-800 flex flex-col gap-5 max-w-2xl mx-auto bg-[#0c0d14]/40">
          <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
            <Briefcase size={16} className="text-purple-400" />
            <span>Create New Job opening</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-400">Job Title</label>
              <input
                type="text"
                required
                placeholder="e.g. Senior Software Engineer"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-400">Department</label>
              <input
                type="text"
                required
                placeholder="e.g. Core Systems Engineering"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-gray-400">Required Skills Core (comma separated)</label>
            <input
              type="text"
              required
              placeholder="e.g. Python, React, TypeScript, FastAPI, PostgreSQL"
              value={requiredSkills}
              onChange={(e) => setRequiredSkills(e.target.value)}
              className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-400">Experience Level</label>
              <input
                type="text"
                required
                placeholder="e.g. 3-5 Years"
                value={experienceLevel}
                onChange={(e) => setExperienceLevel(e.target.value)}
                className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-400">Salary Range</label>
              <input
                type="text"
                required
                placeholder="e.g. $130,000 - $160,000"
                value={salaryRange}
                onChange={(e) => setSalaryRange(e.target.value)}
                className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-400">Office Location</label>
              <input
                type="text"
                required
                placeholder="e.g. San Francisco, CA / Remote"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-gray-400">Position Description</label>
            <textarea
              required
              placeholder="Outline role responsibilities, team structures, and expectation details..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors resize-none leading-relaxed"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-3 text-xs font-bold transition-all shadow-md mt-2"
          >
            Publish Job Listing
          </button>
        </form>
      ) : loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-40 bg-gray-800 rounded animate-pulse" />
          <div className="h-40 bg-gray-800 rounded animate-pulse" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {jobs.map((job) => (
            <div key={job.id} className="glass-panel p-6 rounded-2xl border border-gray-800 bg-[#0c0d14]/40 flex flex-col justify-between gap-4">
              <div>
                <div className="flex justify-between items-start">
                  <h3 className="text-base font-bold text-white">{job.title}</h3>
                  <button
                    onClick={() => handleArchiveJob(job.id)}
                    className="p-2 rounded-xl text-gray-500 hover:text-red-400 hover:bg-red-500/5 border border-transparent transition-colors"
                  >
                    <Trash size={14} />
                  </button>
                </div>
                <p className="text-xs text-purple-400 font-medium mt-1">{job.department} • {job.location}</p>
                <p className="text-xs text-gray-400 mt-3 line-clamp-3 leading-relaxed">{job.description}</p>
                <div className="flex flex-wrap gap-1 mt-4">
                  {(job.required_skills || "").split(",").map((s: string) => (
                    <span key={s} className="text-[9px] px-2 py-0.5 rounded bg-gray-900 text-gray-400 border border-gray-800">
                      {s.trim()}
                    </span>
                  ))}
                </div>
              </div>

              <div className="border-t border-gray-800/80 pt-4 flex justify-between items-center text-[10px] text-gray-500">
                <span>Published: {new Date(job.created_at).toLocaleDateString()}</span>
                <span className="font-bold text-emerald-400">{job.salary_range}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
