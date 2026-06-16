"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import { Sparkles, Terminal, Shield, ArrowRight, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";

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
  const [showPassword, setShowPassword] = useState(false);

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
    <main className="min-h-screen bg-background flex flex-col-reverse md:flex-row relative overflow-hidden">
      {/* Decorative Blur Backgrounds */}
      <div className="absolute top-[-10%] left-[-10%] w-1/2 h-1/2 bg-purple-600/10 rounded-full blur-120 pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-1/2 h-1/2 bg-indigo-600/10 rounded-full blur-120 pointer-events-none" />

      {/* Hero Intro Pane */}
      <div className="flex-1 p-6 md:p-16 flex flex-col justify-between relative z-10">
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
            <span className="block text-10 text-purple-400 font-semibold tracking-wider uppercase">Enterprise Recruiting OS</span>
          </div>
        </div>

        <div className="my-8 md:my-0 max-w-lg">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/40 border border-purple-800/30 text-purple-300 text-xs font-semibold mb-6">
            <Sparkles size={14} className="animate-pulse" />
            <span>Introducing Tush AI Recruiter</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-white leading-[1.15] mb-6">
            The Autonomous <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">
              Recruitment Operating System
            </span>
          </h1>
          <p className="text-gray-400 text-sm md:text-base leading-relaxed mb-8">
            VidyamargAI streamlines screening, creates fully tailored technical assessments, runs proctored tests, conducts video interviews with &nbsp;
            <strong>Tush AI</strong>, and drafts hiring offers.
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-border bg-card">
              <Terminal size={20} className="text-purple-400 mb-2" />
              <h3 className="text-sm font-semibold text-foreground mb-1">AI Orchestration</h3>
              <p className="text-xs text-muted-foreground">12 coordinate agents processing candidates sequentially.</p>
            </div>
            <div className="p-4 rounded-xl border border-border bg-card">
              <Shield size={20} className="text-indigo-400 mb-2" />
              <h3 className="text-sm font-semibold text-foreground mb-1">AI Proctoring</h3>
              <p className="text-xs text-muted-foreground">Tab-monitoring, face detection, and copy-paste warnings.</p>
            </div>
          </div>
        </div>

        <p className="hidden md:block text-xs text-gray-500 font-light">
          © {new Date().getFullYear()} VidyamargAI Tech Systems. All rights secured.
        </p>
      </div>

      {/* Auth Panel Pane */}
      <div className="w-full md:w-480 border-l border-border bg-card/80 backdrop-blur-md p-6 md:p-12 flex flex-col justify-center relative z-10">
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
                  <Alert variant={error.includes("successfully") ? "success" : "error"}>
                    {error}
                  </Alert>
                )}

                {simulatedCode && (
                  <Alert variant="success">
                    [Simulation] Verification code sent: <strong className="font-mono text-sm underline">{simulatedCode}</strong>
                  </Alert>
                )}

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-400">Email Address</label>
                  <Input
                    type="email"
                    required
                    disabled={forgotStep === 2}
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                {forgotStep === 2 && (
                  <>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-gray-400">Verification Code</label>
                      <Input
                        type="text"
                        required
                        placeholder="Enter 6-digit code"
                        value={resetCode}
                        onChange={(e) => setResetCode(e.target.value)}
                        className="font-mono text-center tracking-widest"
                      />
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-gray-400">New Password</label>
                      <div className="relative">
                        <Input
                          type={showPassword ? "text" : "password"}
                          required
                          placeholder="••••••••"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          className="pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors p-1"
                        >
                          {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                    </div>
                  </>
                )}

                <Button
                  type="submit"
                  loading={loading}
                  className="w-full mt-4"
                >
                  {forgotStep === 1 ? "Send Verification Code" : "Update Password"}
                  {!loading && <ArrowRight size={16} />}
                </Button>
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
                <div className="flex bg-muted p-1 rounded-xl mb-6 border border-border">
                  <button
                    type="button"
                    onClick={() => setPortalType("candidate")}
                    className={`flex-1 text-center py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
                      portalType === "candidate" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Candidate Portal
                  </button>
                  <button
                    type="button"
                    onClick={() => setPortalType("admin")}
                    className={`flex-1 text-center py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
                      portalType === "admin" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"
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
                  <Alert variant={error.includes("successfully") ? "success" : "error"}>
                    {error}
                  </Alert>
                )}

                {!isLogin && (
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-400">Full Name</label>
                    <Input
                      type="text"
                      required
                      placeholder="e.g. Liam Smith"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                    />
                  </div>
                )}

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-400">Email Address</label>
                  <Input
                    type="email"
                    required
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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
                        className="text-10 text-purple-400 hover:underline font-medium"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <div className="relative">
                    <Input
                      type={showPassword ? "text" : "password"}
                      required
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors p-1"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  loading={loading}
                  className="w-full mt-4"
                >
                  {isLogin ? "Login" : "Register Profile"}
                  {!loading && <ArrowRight size={16} />}
                </Button>
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
      <footer className="md:hidden w-full text-center py-6 border-t border-gray-900 bg-card/50 relative z-10 mt-auto">
        <p className="text-xs text-gray-500 font-light">
          © {new Date().getFullYear()} VidyamargAI Tech Systems. All rights secured.
        </p>
      </footer>
    </main>
  );
}
