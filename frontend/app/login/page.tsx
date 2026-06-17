"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import { Sparkles, Terminal, ArrowRight, Eye, EyeOff, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import Link from "next/link";

export default function CandidateLogin() {
  const router = useRouter();
  const { login, isAuthenticated, role, initialize } = useAuthStore();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [forgotStep, setForgotStep] = useState(1); // 1 = Enter email, 2 = Enter code & new password
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [theme, setTheme] = useState<"dark" | "light">("light");

  useEffect(() => {
    initialize();
  }, [initialize]);

  // Handle URL reset query parameters and cooldown timer
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const resetEmail = params.get("reset_email");
      const resetCodeParam = params.get("reset_code");
      if (resetEmail && resetCodeParam) {
        setEmail(resetEmail);
        setResetCode(resetCodeParam);
        setIsForgotPassword(true);
        setForgotStep(2);
        setResendCooldown(60);
      }
    }
  }, []);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  // Sync theme state with localStorage & document root
  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") as "dark" | "light" | null;
    if (savedTheme) {
      setTheme(savedTheme);
      if (savedTheme === "light") {
        document.documentElement.classList.add("light-theme");
        document.documentElement.classList.remove("dark");
      } else {
        document.documentElement.classList.remove("light-theme");
        document.documentElement.classList.add("dark");
      }
    } else {
      document.documentElement.classList.add("light-theme");
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("theme", nextTheme);
    if (nextTheme === "light") {
      document.documentElement.classList.add("light-theme");
      document.documentElement.classList.remove("dark");
    } else {
      document.documentElement.classList.remove("light-theme");
      document.documentElement.classList.add("dark");
    }
  };

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
        setError(response.message || "A verification code has been sent to your registered email address.");
        setForgotStep(2);
        setResendCooldown(60);
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
        setError("Password updated successfully! Please log in.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen lg:h-screen lg:overflow-hidden bg-background text-foreground flex relative font-sans">
      {/* Decorative Blur Backgrounds */}
      <div className="absolute top-[-10%] right-[-10%] w-1/2 h-1/2 bg-purple-600/10 rounded-full blur-120 pointer-events-none z-0" />
      <div className="absolute bottom-[-10%] right-1/3 w-1/2 h-1/2 bg-indigo-600/10 rounded-full blur-120 pointer-events-none z-0" />

      {/* LEFT COLUMN: HERO PANEL (Visible on lg and up) */}
      <div className="hidden lg:flex auth-hero-panel bg-gradient-to-br from-slate-50 via-white to-slate-100 text-slate-900 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950 dark:text-white flex-col justify-between p-8 xl:p-12 relative overflow-hidden border-r border-slate-200 dark:border-slate-900 shrink-0 h-full lg:h-screen">
        {/* Background Grid Pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-40 dark:opacity-40 pointer-events-none" />
        
        {/* Glow behind dashboard mockup */}
        <div className="absolute top-2/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-indigo-500/8 dark:bg-indigo-500/15 rounded-full blur-120 pointer-events-none" />

        {/* Top: Logo Branding */}
        <Link href="/" className="flex items-center gap-3 relative z-10 cursor-pointer">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shrink-0 border border-indigo-400/20">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" opacity="0.95"/>
              <path d="M2 17L12 22L22 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M2 12L12 17L22 12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="flex items-baseline gap-0.5">
              <span className="text-slate-900 dark:text-white font-extrabold text-xl tracking-tight leading-none">Vidyamarg</span>
              <span className="text-blue-600 dark:text-blue-400 font-extrabold text-xl tracking-tight leading-none italic">AI</span>
            </div>
            <span className="block text-9 text-indigo-600 dark:text-indigo-400 font-bold tracking-widest uppercase mt-1">Enterprise Recruiting OS</span>
          </div>
        </Link>

        {/* Center: Headline & Premium Live Mockup Dashboard */}
        <div className="my-auto flex flex-col gap-6 lg:gap-5 xl:gap-8 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/60 text-indigo-600 dark:bg-purple-500/10 dark:border-purple-500/20 dark:text-purple-300 text-xs font-semibold mb-4 lg:mb-3 xl:mb-5">
              <Sparkles size={13} className="animate-pulse text-indigo-500 dark:text-purple-400" />
              <span>Introducing Tush AI Recruiter v2</span>
            </div>
            <h1 className="text-3xl lg:text-4xl xl:text-5xl font-black leading-[1.12] tracking-tight">
              <span className="text-slate-900 dark:text-white">The Autonomous</span> <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 dark:from-purple-400 dark:via-indigo-300 dark:to-blue-400">
                Recruitment OS
              </span>
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed mt-3 lg:mt-2 xl:mt-4 max-w-md">
              VidyamargAI coordinates assessments, proctors exams, conducts interviews with <strong className="text-slate-700 dark:text-slate-200">Tush AI</strong>, and streamlines full candidate pipelines.
            </p>
          </div>

          {/* Premium Terminal Mockup */}
          <div className="bg-white border border-slate-200 shadow-terminal-light dark:bg-slate-900/40 dark:border-slate-800 dark:shadow-2xl dark:backdrop-blur-xl p-4 lg:p-4 xl:p-5 rounded-2xl relative w-full overflow-hidden max-w-md xl:max-w-lg">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800/80 pb-2 mb-3 lg:pb-2 lg:mb-2.5 xl:pb-3 xl:mb-4">
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400 dark:bg-red-500/60" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400 dark:bg-amber-500/60" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 dark:bg-emerald-500/60" />
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 bg-indigo-50 border border-indigo-200/60 dark:bg-slate-950/50 dark:border-slate-800/60 rounded-lg text-9 font-mono text-indigo-600 dark:text-slate-500">
                <Terminal size={10} className="text-indigo-500 dark:text-indigo-400" />
                <span>tush-ai-orchestrator.sh</span>
              </div>
            </div>

            <div className="font-mono text-10 text-slate-500 dark:text-slate-400 flex flex-col gap-2 lg:gap-1.5 xl:gap-2.5 leading-relaxed">
              <div className="flex gap-2">
                <span className="text-blue-600 dark:text-indigo-400 font-bold shrink-0">[16:43:46]</span>
                <span>Agent <span className="text-slate-900 dark:text-white font-bold">#01_screener</span> active: parsed candidate folder.</span>
              </div>
              <div className="flex gap-2">
                <span className="text-blue-600 dark:text-indigo-400 font-bold shrink-0">[16:43:48]</span>
                <span>Proctor status: <span className="text-emerald-600 dark:text-emerald-400 font-bold">Active</span>. Checking face verification loop.</span>
              </div>
              <div className="flex gap-2">
                <span className="text-blue-600 dark:text-indigo-400 font-bold shrink-0">[16:43:52]</span>
                <span>Tush AI Interviewer: <span className="text-purple-600 dark:text-purple-400 font-bold">speaking</span>, latency 82ms.</span>
              </div>
              <div className="flex gap-2 border-t border-slate-200/80 dark:border-slate-800/50 pt-2 lg:pt-1.5 xl:pt-2.5 mt-0.5">
                <span className="text-emerald-600 dark:text-emerald-400 font-bold">PIPELINE VERIFIED:</span>
                <span className="text-slate-900 dark:text-white">Liam Smith matched 96% with position terms.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom: Footer */}
        <p className="text-xs text-slate-400 dark:text-slate-600 font-light relative z-10 mt-4">
          © {new Date().getFullYear()} VidyamargAI Tech Systems. All rights secured.
        </p>
      </div>

      {/* RIGHT COLUMN: AUTH PANEL */}
      <div className="flex-1 lg:auth-form-panel flex flex-col justify-between p-6 lg:p-8 xl:p-12 min-h-screen lg:h-screen lg:overflow-y-auto bg-background relative z-10">
        
        {/* Top bar: Theme switcher */}
        <header className="flex justify-between items-center w-full mb-8 lg:mb-4 xl:mb-8 flex-shrink-0">
          {/* Logo Branding visible ONLY on mobile */}
          <Link href="/" className="flex items-center gap-2.5 lg:hidden">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-md shrink-0">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" opacity="0.95"/>
                <path d="M2 17L12 22L22 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div className="flex items-baseline gap-0.5">
                <span className="text-foreground font-black text-base tracking-tight leading-none">Vidyamarg</span>
                <span className="text-blue-500 font-black text-base tracking-tight leading-none italic">AI</span>
              </div>
              <span className="block text-8 text-muted-foreground font-bold tracking-wider uppercase mt-0.5">Candidate Portal</span>
            </div>
          </Link>

          <div className="hidden lg:block" />

          {/* Floating Theme Switcher */}
          <button
            onClick={toggleTheme}
            className="p-2.5 rounded-xl border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-all shadow-sm cursor-pointer"
            title="Toggle theme"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </header>

        {/* Center: Auth Form Container */}
        <div className="w-full max-w-md mx-auto my-auto py-8 lg:py-4 xl:py-8 flex-shrink-0">
          {isForgotPassword ? (
            /* Forgot Password Flow */
            <div>
              <div className="mb-8 lg:mb-4 xl:mb-8">
                <h2 className="text-2xl font-extrabold text-foreground tracking-tight mb-2">Reset password</h2>
                <p className="text-xs font-semibold text-muted-foreground leading-relaxed">
                  {forgotStep === 1 
                    ? "Enter your email address to receive a verification code." 
                    : "Enter the code sent to your email and your new password."}
                </p>
              </div>

              <form onSubmit={handleForgotPasswordSubmit} className="flex flex-col gap-4 lg:gap-3 xl:gap-4">
                {error && (
                  <Alert variant={error.includes("successfully") || error.includes("verification code has been sent") ? "success" : "error"}>
                    {error}
                  </Alert>
                )}

                <div className="flex flex-col gap-1.5">
                  <label className="text-11 font-bold text-muted-foreground uppercase tracking-wider mb-1 block">Email Address</label>
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
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-11 font-bold text-muted-foreground uppercase tracking-wider block">Verification Code</label>
                        <button
                          type="button"
                          disabled={resendCooldown > 0 || loading}
                          onClick={async () => {
                            setError("");
                            setLoading(true);
                            try {
                              const response = await apiService.forgotPassword(email);
                              setError(response.message || "A verification code has been sent to your registered email address.");
                              setResendCooldown(60);
                            } catch (err: any) {
                              setError(err.message || "Failed to resend verification code.");
                            } finally {
                              setLoading(false);
                            }
                          }}
                          className="text-[10px] text-indigo-600 dark:text-indigo-400 hover:underline font-bold disabled:text-muted-foreground disabled:no-underline disabled:cursor-not-allowed cursor-pointer"
                        >
                          {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend OTP"}
                        </button>
                      </div>
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
                      <label className="text-11 font-bold text-muted-foreground uppercase tracking-wider mb-1 block">New Password</label>
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
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1"
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
                  className="w-full mt-4 lg:mt-2 xl:mt-4"
                >
                  {forgotStep === 1 ? "Send Verification Code" : "Update Password"}
                  {!loading && <ArrowRight size={16} />}
                </Button>
              </form>

              <div className="mt-8 lg:mt-4 xl:mt-8 text-center">
                <button
                  onClick={() => {
                    setError("");
                    setIsForgotPassword(false);
                    setForgotStep(1);
                  }}
                  className="text-xs text-purple-600 dark:text-purple-400 hover:underline font-bold cursor-pointer"
                >
                  Back to login
                </button>
              </div>
            </div>
          ) : (
            /* Candidate Login Flow */
            <div>
              <div className="mb-8 lg:mb-4 xl:mb-8">
                <h2 className="text-2xl font-extrabold text-foreground tracking-tight mb-2">
                  Candidate Login
                </h2>
                <p className="text-xs font-semibold text-muted-foreground leading-relaxed">
                  Enter your credentials to enter the VidyamargAI Candidate Portal.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="flex flex-col gap-4 lg:gap-3 xl:gap-4">
                {error && (
                  <Alert variant={error.includes("successfully") ? "success" : "error"}>
                    {error}
                  </Alert>
                )}

                <div className="flex flex-col gap-1.5">
                  <label className="text-11 font-bold text-muted-foreground uppercase tracking-wider mb-1 block">Email Address</label>
                  <Input
                    type="email"
                    required
                    placeholder="name@gmail.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-11 font-bold text-muted-foreground uppercase tracking-wider mb-1 block">Security Password</label>
                    <button
                      type="button"
                      onClick={() => {
                        setError("");
                        setIsForgotPassword(true);
                        setForgotStep(1);
                      }}
                      className="text-10 text-purple-600 dark:text-purple-400 hover:underline font-bold cursor-pointer"
                    >
                      Forgot password?
                    </button>
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
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1 cursor-pointer"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  loading={loading}
                  className="w-full mt-4 lg:mt-2 xl:mt-4"
                >
                  <span>Login</span>
                  {!loading && <ArrowRight size={16} />}
                </Button>
              </form>

              <div className="mt-8 lg:mt-6 lg:pt-4 xl:mt-8 xl:pt-6 text-center border-t border-border flex flex-col gap-2">
                <Link
                  href="/signup"
                  className="text-xs text-purple-600 dark:text-purple-400 hover:underline font-bold"
                >
                  New to VidyamargAI? Setup a Candidate account
                </Link>
                <Link
                  href="/admin-login"
                  className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Are you an Administrator? Go to Admin Console
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Copyright visible ONLY on mobile */}
        <footer className="lg:hidden w-full text-center py-4 mt-8 flex-shrink-0">
          <p className="text-xs text-muted-foreground font-light">
            © {new Date().getFullYear()} VidyamargAI Tech Systems. All rights secured.
          </p>
        </footer>
      </div>
    </main>
  );
}
