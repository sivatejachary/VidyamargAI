"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import { Sparkles, Terminal, Shield, ArrowRight } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const { login, isAuthenticated, role, initialize } = useAuthStore();
  
  const [isLogin, setIsLogin] = useState(true);
  const [portalType, setPortalType] = useState<"candidate" | "admin">("candidate");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (isAuthenticated) {
      if (role === "admin" || role === "super_admin") {
        router.push("/admin");
      } else {
        router.push("/candidate");
      }
    }
  }, [isAuthenticated, role, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        // Authenticate
        const params = new URLSearchParams();
        params.append("username", email);
        params.append("password", password);
        
        const tokenData = await apiService.login(params);
        login(tokenData.access_token, tokenData.role, tokenData.full_name, tokenData.email);
        
        if (tokenData.role === "admin" || tokenData.role === "super_admin") {
          router.push("/admin");
        } else {
          router.push("/candidate");
        }
      } else {
        // Sign Up
        await apiService.signup({
          email,
          password,
          full_name: fullName,
          role: portalType
        });
        setIsLogin(true);
        setError("Account created successfully! Please log in.");
      }
    } catch (err: any) {
      setError(err.message || "An authentication error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#07070b] flex flex-col md:flex-row relative overflow-hidden">
      {/* Decorative Blur Backgrounds */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Hero Intro Pane */}
      <div className="flex-1 p-8 md:p-16 flex flex-col justify-between relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-tara flex items-center justify-center font-bold text-white shadow-lg">
            H
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white leading-tight">HireAI</span>
            <span className="block text-[10px] text-purple-400 font-semibold tracking-wider uppercase">Enterprise Recruiting OS</span>
          </div>
        </div>

        <div className="my-12 md:my-0 max-w-lg">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/40 border border-purple-800/30 text-purple-300 text-xs font-semibold mb-6">
            <Sparkles size={14} className="animate-pulse" />
            <span>Introducing Tara AI Recruiter</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white leading-[1.15] mb-6">
            The Autonomous <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">
              Recruitment Operating System
            </span>
          </h1>
          <p className="text-gray-400 text-base leading-relaxed mb-8">
            HireAI streamlines screening, creates fully tailored technical assessments, runs proctored tests, conducts video interviews with 
            <strong> Tara AI</strong>, and drafts hiring offers.
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-gray-800 bg-[#0d0e15]/60">
              <Terminal size={20} className="text-purple-400 mb-2" />
              <h3 className="text-sm font-semibold text-white mb-1">AI Orchestration</h3>
              <p className="text-xs text-gray-500">12 coordinate agents processing candidates sequentially.</p>
            </div>
            <div className="p-4 rounded-xl border border-gray-800 bg-[#0d0e15]/60">
              <Shield size={20} className="text-indigo-400 mb-2" />
              <h3 className="text-sm font-semibold text-white mb-1">AI Proctoring</h3>
              <p className="text-xs text-gray-500">Tab-monitoring, face detection, and copy-paste warnings.</p>
            </div>
          </div>
        </div>

        <p className="text-xs text-gray-500 font-light">
          © {new Date().getFullYear()} HireAI Tech Systems. All rights secured.
        </p>
      </div>

      {/* Auth Panel Pane */}
      <div className="w-full md:w-[480px] border-l border-gray-900 bg-[#0d0e15]/50 backdrop-blur-md p-8 md:p-12 flex flex-col justify-center relative z-10">
        <div className="w-full max-w-md mx-auto">
          {/* Portal Switcher */}
          {!isLogin && (
            <div className="flex bg-[#12131e] p-1 rounded-xl mb-6 border border-gray-800">
              <button
                type="button"
                onClick={() => setPortalType("candidate")}
                className={`flex-1 text-center py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
                  portalType === "candidate" ? "bg-purple-600 text-white shadow" : "text-gray-400 hover:text-white"
                }`}
              >
                Candidate Portal
              </button>
              <button
                type="button"
                onClick={() => setPortalType("admin")}
                className={`flex-1 text-center py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
                  portalType === "admin" ? "bg-purple-600 text-white shadow" : "text-gray-400 hover:text-white"
                }`}
              >
                Recruiter Admin
              </button>
            </div>
          )}

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">
              {isLogin ? "Welcome back" : "Create candidate profile"}
            </h2>
            <p className="text-sm text-gray-400">
              {isLogin 
                ? "Enter your credentials to enter the HireAI OS portal" 
                : `Join the platform as a ${portalType === "admin" ? "Recruiting Administrator" : "Job Seeking Candidate"}`}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {error && (
              <div className={`p-3 rounded-xl text-xs font-medium border ${
                error.includes("successfully") 
                  ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-400" 
                  : "bg-red-950/20 border-red-800/40 text-red-400"
              }`}>
                {error}
              </div>
            )}

            {!isLogin && (
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-gray-400">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Liam Smith"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500 transition-colors"
                />
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-400">Email Address</label>
              <input
                type="email"
                required
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-400">Security Password</label>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-3 text-sm font-semibold flex items-center justify-center gap-2 mt-4 hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-200 disabled:opacity-50"
            >
              {loading ? "Authenticating..." : isLogin ? "Access Dashboard" : "Register Profile"}
              {!loading && <ArrowRight size={16} />}
            </button>
          </form>

          <div className="mt-8 text-center">
            <button
              onClick={() => {
                setError("");
                setIsLogin(!isLogin);
              }}
              className="text-xs text-purple-400 hover:underline font-medium"
            >
              {isLogin ? "New to HireAI? Setup an account" : "Already registered? Login here"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
