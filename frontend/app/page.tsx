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

  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [forgotStep, setForgotStep] = useState(1); // 1 = Enter email, 2 = Enter code & new password
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [simulatedCode, setSimulatedCode] = useState("");

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
        
        // Log in immediately
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
      }
    } catch (err: any) {
      setError(err.message || "An authentication error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (forgotStep === 1) {
        const response = await apiService.forgotPassword(email);
        setSimulatedCode(response.code);
        setForgotStep(2);
      } else {
        await apiService.resetPassword({
          email,
          new_password: newPassword,
          code: resetCode
        });
        setError("");
        setIsForgotPassword(false);
        setForgotStep(1);
        setResetCode("");
        setNewPassword("");
        setSimulatedCode("");
        setError("Password updated successfully! Please log in.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to reset password.");
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
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shrink-0">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" opacity="0.9"/>
              <path d="M2 17L12 22L22 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M2 12L12 17L22 12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="flex items-baseline gap-0">
              <span className="text-white font-extrabold text-xl tracking-tight">Vidyamarg</span>
              <span className="text-blue-500 font-extrabold text-xl tracking-tight italic">AI</span>
            </div>
            <span className="block text-[10px] text-purple-400 font-semibold tracking-wider uppercase">Enterprise Recruiting OS</span>
          </div>
        </div>

        <div className="my-12 md:my-0 max-w-lg">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/40 border border-purple-800/30 text-purple-300 text-xs font-semibold mb-6">
            <Sparkles size={14} className="animate-pulse" />
            <span>Introducing Tush AI Recruiter</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white leading-[1.15] mb-6">
            The Autonomous <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">
              Recruitment Operating System
            </span>
          </h1>
          <p className="text-gray-400 text-base leading-relaxed mb-8">
            VidyamargAI streamlines screening, creates fully tailored technical assessments, runs proctored tests, conducts video interviews with 
            <strong> Tush AI</strong>, and drafts hiring offers.
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

        <p className="hidden md:block text-xs text-gray-500 font-light">
          © {new Date().getFullYear()} VidyamargAI Tech Systems. All rights secured.
        </p>
      </div>

      {/* Auth Panel Pane */}
      <div className="w-full md:w-[480px] border-l border-gray-900 bg-[#0d0e15]/50 backdrop-blur-md p-8 md:p-12 flex flex-col justify-center relative z-10">
        <div className="w-full max-w-md mx-auto">
          {isForgotPassword ? (
            /* Forgot Password Flow */
            <div>
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-white mb-2">Reset password</h2>
                <p className="text-sm text-gray-400">
                  {forgotStep === 1 
                    ? "Enter your email address to receive a verification code" 
                    : "Enter the code sent to your email and your new password"}
                </p>
              </div>

              <form onSubmit={handleForgotPasswordSubmit} className="flex flex-col gap-4">
                {error && (
                  <div className={`p-3 rounded-xl text-xs font-medium border ${
                    error.includes("successfully") 
                      ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-400" 
                      : "bg-red-950/20 border-red-800/40 text-red-400"
                  }`}>
                    {error}
                  </div>
                )}

                {simulatedCode && (
                  <div className="p-3 rounded-xl text-xs font-medium border bg-blue-950/20 border-blue-800/40 text-blue-400">
                    [Simulation] Verification code sent: <strong className="font-mono text-sm underline">{simulatedCode}</strong>
                  </div>
                )}

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-400">Email Address</label>
                  <input
                    type="email"
                    required
                    disabled={forgotStep === 2}
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500 transition-colors disabled:opacity-50"
                  />
                </div>

                {forgotStep === 2 && (
                  <>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-gray-400">Verification Code</label>
                      <input
                        type="text"
                        required
                        placeholder="Enter 6-digit code"
                        value={resetCode}
                        onChange={(e) => setResetCode(e.target.value)}
                        className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500 transition-colors font-mono text-center tracking-widest"
                      />
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-gray-400">New Password</label>
                      <input
                        type="password"
                        required
                        placeholder="••••••••"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500 transition-colors"
                      />
                    </div>
                  </>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-3 text-sm font-semibold flex items-center justify-center gap-2 mt-4 hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-200 disabled:opacity-50"
                >
                  {loading ? "Processing..." : forgotStep === 1 ? "Send Verification Code" : "Update Password"}
                  {!loading && <ArrowRight size={16} />}
                </button>
              </form>

              <div className="mt-8 text-center">
                <button
                  onClick={() => {
                    setError("");
                    setIsForgotPassword(false);
                    setForgotStep(1);
                    setSimulatedCode("");
                  }}
                  className="text-xs text-purple-400 hover:underline font-medium"
                >
                  Back to login
                </button>
              </div>
            </div>
          ) : (
            /* Normal Login/Signup Flow */
            <div>
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
                    ? "Enter your credentials to enter the VidyamargAI OS portal" 
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
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-semibold text-gray-400">Security Password</label>
                    {isLogin && (
                      <button
                        type="button"
                        onClick={() => {
                          setError("");
                          setIsForgotPassword(true);
                          setForgotStep(1);
                          setSimulatedCode("");
                        }}
                        className="text-[10px] text-purple-400 hover:underline font-medium"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
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
                  {loading ? "Authenticating..." : isLogin ? "Login" : "Register Profile"}
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
                  {isLogin ? "New to VidyamargAI? Setup an account" : "Already registered? Login here"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Copyright Footer */}
      <footer className="md:hidden w-full text-center py-6 border-t border-gray-900 bg-[#0d0e15]/50 relative z-10 mt-auto">
        <p className="text-xs text-gray-500 font-light">
          © {new Date().getFullYear()} VidyamargAI Tech Systems. All rights secured.
        </p>
      </footer>
    </main>
  );
}
