"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { User, Globe, CheckCircle, Phone, MapPin, Link2, Code2, Briefcase, GraduationCap, Award, Edit3 } from "lucide-react";

export default function CandidateProfile() {
  const { fullName, email } = useAuthStore();
  
  // Profile fields state
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [education, setEducation] = useState("");
  const [experience, setExperience] = useState("");
  const [skills, setSkills] = useState("");
  const [certifications, setCertifications] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [github, setGithub] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [parsedName, setParsedName] = useState("");
  const [parsedEmail, setParsedEmail] = useState("");
  
  // UI States
  const [isEditMode, setIsEditMode] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState("");

  const loadProfile = async () => {
    try {
      const data = await apiService.getProfile();
      setPhone(data.phone || "");
      setAddress(data.address || "");
      setSkills(data.skills || "");
      setCertifications(data.certifications || "");
      setLinkedin(data.linkedin || "");
      setGithub(data.github || "");
      setPortfolio(data.portfolio || "");
      setParsedName(data.parsed_name || "");
      setParsedEmail(data.parsed_email || "");

      // Format education JSON for input form
      if (data.education) {
        try {
          const parsedEdu = JSON.parse(data.education);
          if (Array.isArray(parsedEdu)) {
            setEducation(JSON.stringify(parsedEdu, null, 2));
          } else {
            setEducation(data.education);
          }
        } catch {
          setEducation(data.education);
        }
      }
      
      // Format experience JSON for input form
      if (data.experience) {
        try {
          const parsedExp = JSON.parse(data.experience);
          if (Array.isArray(parsedExp)) {
            setExperience(JSON.stringify(parsedExp, null, 2));
          } else {
            setExperience(data.experience);
          }
        } catch {
          setExperience(data.experience);
        }
      }
    } catch (err) {
      console.error("Failed to load profile:", err);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(false);
    setError("");
    try {
      await apiService.updateProfile({
        phone,
        address,
        education,
        experience,
        skills,
        certifications,
        linkedin,
        github,
        portfolio
      });
      setSaveSuccess(true);
      setIsEditMode(false);
      await loadProfile();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to update profile details.");
    }
  };


  // Safe JSON Parsing helper for rendering view
  const parseJsonArray = (jsonStr: string) => {
    if (!jsonStr) return [];
    try {
      const parsed = JSON.parse(jsonStr);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      // Return a single item array if it's plain text
      return [{ description: jsonStr }];
    }
  };

  const eduList = parseJsonArray(education);
  const expList = parseJsonArray(experience);
  const skillsList = skills ? skills.split(",").map(s => s.trim()).filter(Boolean) : [];

  return (
    <div className="w-full min-h-screen bg-background dark:bg-background p-6 font-sans text-gray-800 dark:text-gray-100 transition-colors duration-300">
      
      {/* Header Profile Title and Mode switch */}
      <div className="border-b border-gray-200 dark:border-gray-850 pb-5 mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">Profile Workspace</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-normal">
            Manage your personal data, view extracted skills from your resume, or modify profile fields manually.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsEditMode(!isEditMode)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
              isEditMode 
                ? "bg-gray-150 border-gray-300 dark:bg-gray-800 dark:border-gray-700 text-gray-700 dark:text-gray-200"
                : "bg-indigo-500/10 border-indigo-500/20 hover:bg-indigo-500/20 text-indigo-500"
            }`}
          >
            <Edit3 size={13} />
            <span>{isEditMode ? "View Profile" : "Edit Profile"}</span>
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div className="p-3 mb-6 rounded-xl bg-emerald-950/20 border border-emerald-800/40 text-emerald-400 text-xs font-semibold flex items-center gap-2">
          <CheckCircle size={16} />
          <span>Profile changes updated successfully!</span>
        </div>
      )}

      {error && (
        <div className="p-3 mb-6 rounded-xl bg-red-950/20 border border-red-800/40 text-red-400 text-xs font-semibold">
          {error}
        </div>
      )}

      {!isEditMode ? (
        // --- VIEW PROFILE MODE ---
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Side: Avatar, Contacts, Skills (5/12 width) */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            
            {/* User Main Card */}
            <div className="bg-white dark:bg-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm flex flex-col items-center text-center gap-4">
              <div className="w-20 h-20 rounded-full bg-purple-100 dark:bg-purple-900/35 border-2 border-purple-200 dark:border-purple-800 flex items-center justify-center font-extrabold text-3xl text-purple-600 dark:text-purple-300 shadow-sm">
                {parsedName ? parsedName[0].toUpperCase() : (fullName ? fullName[0].toUpperCase() : "?")}
              </div>
              <div>
                <h2 className="text-base font-bold text-gray-950 dark:text-white">{parsedName || fullName || "Not specified"}</h2>
                <span className="text-xs text-gray-400 block mt-1">{parsedEmail || email || "Not specified"}</span>
              </div>
              
              {/* Social icons */}
              <div className="flex gap-3 mt-1.5">
                {linkedin && (
                  <a href={linkedin} target="_blank" rel="noopener noreferrer" className="p-2 border border-gray-200 dark:border-gray-800 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-900 text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors" title="LinkedIn Profile">
                    <Link2 size={15} />
                  </a>
                )}
                {github && (
                  <a href={github} target="_blank" rel="noopener noreferrer" className="p-2 border border-gray-200 dark:border-gray-800 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-900 text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors" title="GitHub Profile">
                    <Code2 size={15} />
                  </a>
                )}
                {portfolio && (
                  <a href={portfolio} target="_blank" rel="noopener noreferrer" className="p-2 border border-gray-200 dark:border-gray-800 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-900 text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
                    <Globe size={15} />
                  </a>
                )}
              </div>
            </div>

            {/* General Information Card */}
            <div className="bg-white dark:bg-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm flex flex-col gap-4">
              <h3 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider border-b border-gray-100 dark:border-gray-850 pb-2">
                Contact & Details
              </h3>
              
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-xs">
                  <Phone size={14} className="text-gray-400 shrink-0" />
                  <div>
                    <span className="text-gray-400 block text-9 uppercase font-bold tracking-wider">Phone</span>
                    <span className="text-gray-700 dark:text-gray-250 font-semibold">{phone || "Not listed"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <MapPin size={14} className="text-gray-400 shrink-0" />
                  <div>
                    <span className="text-gray-400 block text-9 uppercase font-bold tracking-wider">Address</span>
                    <span className="text-gray-700 dark:text-gray-250 font-semibold">{address || "Not listed"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <Award size={14} className="text-gray-400 shrink-0" />
                  <div>
                    <span className="text-gray-400 block text-9 uppercase font-bold tracking-wider">Certifications</span>
                    <span className="text-gray-700 dark:text-gray-250 font-semibold">{certifications || "No certifications listed"}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Extracted Skills tag list */}
            <div className="bg-white dark:bg-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm flex flex-col gap-4">
              <h3 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider border-b border-gray-100 dark:border-gray-850 pb-2">
                Core Competencies
              </h3>
              {skillsList.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No skills listed. Please upload your resume PDF on the Resume Builder page to extract them automatically.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {skillsList.map((sk) => (
                    <span 
                      key={sk}
                      className="text-xs font-bold px-3 py-1 rounded-xl bg-purple-50 dark:bg-purple-950/20 text-indigo-500 dark:text-purple-300 border border-purple-100/40 dark:border-purple-900/10 shadow-sm"
                    >
                      {sk}
                    </span>
                  ))}
                </div>
              )}
            </div>

          </div>

          {/* Right Side: Timeline Experience & Education (7/12 width) */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            
            {/* Experience Timeline */}
            <div className="bg-white dark:bg-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm flex flex-col gap-5">
              <h3 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider border-b border-gray-100 dark:border-gray-850 pb-2 flex items-center gap-1.5">
                <Briefcase size={14} className="text-indigo-500" />
                <span>Employment History</span>
              </h3>

              {expList.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No experience history found. Please upload a resume on the Resume Builder page to parse details automatically, or edit your profile manually.</p>
              ) : (
                <div className="relative border-l border-gray-200 dark:border-gray-800 ml-3.5 pl-6 space-y-6 py-1">
                  {expList.map((exp: any, idx: number) => (
                    <div key={idx} className="relative">
                      {/* Timeline dot */}
                      <span className="absolute left-minus-31 top-1.5 flex h-3 w-3 items-center justify-center rounded-full bg-white dark:bg-background border-2 border-indigo-500" />
                      
                      <div>
                        <h4 className="text-xs font-bold text-gray-950 dark:text-white">
                          {exp.role || "Not specified"}
                        </h4>
                        <span className="text-10 font-bold text-gray-400 block mt-0.5">
                          {exp.company || "Not specified"} • {exp.years ? `${exp.years} Yrs` : "Date unspecified"}
                        </span>
                        <p className="text-xs text-gray-500 mt-2 leading-relaxed">
                          {exp.description || ""}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Education Timeline */}
            <div className="bg-white dark:bg-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm flex flex-col gap-5">
              <h3 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider border-b border-gray-100 dark:border-gray-850 pb-2 flex items-center gap-1.5">
                <GraduationCap size={14} className="text-indigo-500" />
                <span>Education Background</span>
              </h3>

              {eduList.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No education history found. Please upload a resume on the Resume Builder page to parse details automatically, or edit your profile manually.</p>
              ) : (
                <div className="relative border-l border-gray-200 dark:border-gray-800 ml-3.5 pl-6 space-y-6 py-1">
                  {eduList.map((edu: any, idx: number) => (
                    <div key={idx} className="relative">
                      {/* Timeline dot */}
                      <span className="absolute left-minus-31 top-1.5 flex h-3 w-3 items-center justify-center rounded-full bg-white dark:bg-background border-2 border-purple-500" />
                      
                      <div>
                        <h4 className="text-xs font-bold text-gray-950 dark:text-white">
                          {edu.degree || "Not specified"}
                        </h4>
                        <span className="text-10 font-bold text-gray-400 block mt-0.5">
                          {edu.school || "Not specified"} • {edu.year || "Year unspecified"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>

        </div>
      ) : (
        // --- EDIT PROFILE MODE (FORM INPUTS) ---
        <div className="max-w-4xl mx-auto bg-white dark:bg-card border border-gray-200 dark:border-gray-800 rounded-3xl p-6 shadow-sm">
          <form onSubmit={handleSaveProfile} className="flex flex-col gap-6">
            
            <div className="flex items-center gap-2 border-b border-gray-100 dark:border-gray-850 pb-3">
              <User size={16} className="text-indigo-500" />
              <h2 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider">General Information</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500">Phone Number</label>
                <input
                  type="text"
                  placeholder="+1 (555) 019-9238"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="bg-white dark:bg-card border border-gray-250 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500">Physical Address</label>
                <input
                  type="text"
                  placeholder="San Francisco, CA"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="bg-white dark:bg-card border border-gray-250 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-500">Skills Core Competencies (comma separated)</label>
              <textarea
                placeholder="Python, React, TypeScript, FastAPI, WebSockets, PostgreSQL, Docker"
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
                rows={2}
                className="bg-white dark:bg-card border border-gray-250 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-500">Certifications & Credentials (comma separated)</label>
              <input
                type="text"
                placeholder="AWS Solution Architect, Kubernetes CKA"
                value={certifications}
                onChange={(e) => setCertifications(e.target.value)}
                className="bg-white dark:bg-card border border-gray-250 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500">Education Background (JSON Array)</label>
                <textarea
                  placeholder='[\n  {\n    "degree": "BS in CS",\n    "school": "University Name",\n    "year": "2023"\n  }\n]'
                  value={education}
                  onChange={(e) => setEducation(e.target.value)}
                  rows={5}
                  className="bg-white dark:bg-card border border-gray-255 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500 font-mono resize-none"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500">Employment History (JSON Array)</label>
                <textarea
                  placeholder='[\n  {\n    "role": "Software Engineer",\n    "company": "Company Name",\n    "years": 3,\n    "description": "Built core services..."\n  }\n]'
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  rows={5}
                  className="bg-white dark:bg-card border border-gray-255 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500 font-mono resize-none"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 border-b border-gray-100 dark:border-gray-850 pb-3 mt-2">
              <Globe size={16} className="text-indigo-500" />
              <h2 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider">Social Links & Portfolios</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500">LinkedIn Link</label>
                <input
                  type="url"
                  placeholder="https://linkedin.com/in/username"
                  value={linkedin}
                  onChange={(e) => setLinkedin(e.target.value)}
                  className="bg-white dark:bg-card border border-gray-250 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500">GitHub Link</label>
                <input
                  type="url"
                  placeholder="https://github.com/username"
                  value={github}
                  onChange={(e) => setGithub(e.target.value)}
                  className="bg-white dark:bg-card border border-gray-250 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-500">Portfolio Website</label>
                <input
                  type="url"
                  placeholder="https://username.dev"
                  value={portfolio}
                  onChange={(e) => setPortfolio(e.target.value)}
                  className="bg-white dark:bg-card border border-gray-250 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-800 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-4">
              <button
                type="submit"
                className="flex-1 bg-indigo-500 hover:bg-indigo-650 text-white rounded-xl py-2.5 text-xs font-bold transition-all shadow-sm cursor-pointer"
              >
                Save Information
              </button>
              <button
                type="button"
                onClick={() => setIsEditMode(false)}
                className="px-6 py-2.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-750 text-gray-700 dark:text-gray-200 rounded-xl text-xs font-bold transition-all cursor-pointer border border-transparent dark:border-gray-700"
              >
                Cancel
              </button>
            </div>

          </form>
        </div>
      )}

    </div>
  );
}
