"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import { 
  Sparkles, Briefcase, FileText, Compass, Trophy, MessageSquare, 
  Bell, Moon, Sun, LogOut, LayoutDashboard, Users, 
  GitFork, Cpu, PanelLeftClose, PanelLeftOpen, Menu, X, BookOpen, Bot
} from "lucide-react";

interface SidebarProps {
  portal: "candidate" | "admin";
}

export default function Sidebar({ portal }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, fullName, email } = useAuthStore();
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    // Read synchronously from localStorage to prevent theme flicker on navigation
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("theme");
      if (saved === "dark" || saved === "light") return saved;
    }
    return "light";
  });
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);


  useEffect(() => {
    const fetchPreferences = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;
        const prefs = await apiService.getPreferences();
        if (prefs && prefs.theme) {
          const fetchedTheme = prefs.theme as "dark" | "light";
          setTheme(fetchedTheme);
          localStorage.setItem("theme", fetchedTheme);
          if (fetchedTheme === "light") {
            document.documentElement.classList.add("light-theme");
            document.documentElement.classList.remove("dark");
          } else {
            document.documentElement.classList.remove("light-theme");
            document.documentElement.classList.add("dark");
          }
        }
      } catch (err) {
        console.error("Failed to fetch user preferences:", err);
      }
    };

    fetchPreferences();

    const savedTheme = localStorage.getItem("theme") as "dark" | "light" | null;
    if (savedTheme) {
      setTimeout(() => {
        setTheme(savedTheme);
      }, 0);
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

    // Restore collapsed state
    const savedCollapsed = localStorage.getItem("sidebar_collapsed");
    if (savedCollapsed === "true") {
      setTimeout(() => {
        setCollapsed(true);
      }, 0);
    }
  }, []);

  const toggleTheme = async () => {
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

    try {
      const token = localStorage.getItem("token");
      if (token) {
        await apiService.updatePreferences(nextTheme);
      }
    } catch (err) {
      console.error("Failed to save user theme preference:", err);
    }
  };

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("sidebar_collapsed", String(next));
  };

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  const handleProfileClick = () => {
    if (portal === "candidate") {
      router.push("/candidate/profile");
    }
  };

  const candidateLinks = [
    { name: "AI Job Agent", href: "/candidate/job-agent", icon: Bot, highlight: true },
    { name: "Ask Tush AI", href: "/candidate/chat", icon: Sparkles },
    { name: "Resume Builder", href: "/candidate/resume", icon: FileText },
    { name: "Skill Lab", href: "/candidate/skill-lab", icon: Compass },
    { name: "Hackathons", href: "/candidate/hackathons", icon: Trophy },
    { name: "Messages", href: "/candidate/messages", icon: MessageSquare },
    { name: "Notifications", href: "/candidate/notifications", icon: Bell }
  ];

  const adminLinks = [
    { name: "Overview", href: "/admin", icon: LayoutDashboard },
    { name: "Students", href: "/admin/candidates", icon: Users },
    { name: "Course Management", href: "/admin/courses", icon: BookOpen }
  ];

  const activeLinks = portal === "candidate" ? candidateLinks : adminLinks;

  const userInitial = fullName ? fullName[0].toUpperCase() : "U";
  const displayName = fullName ? fullName.toLowerCase() : "user";
  const displayEmail = email || "";

  return (
    <>
      {/* Mobile Sticky Top Header */}
      <header className="md:hidden flex items-center px-4 py-3 bg-app-surface border-b border-app-border fixed top-0 left-0 right-0 z-40 h-16 w-full font-sans">
        <button 
          onClick={() => setMobileOpen(true)}
          className="text-app-text-muted hover:text-app-text p-2 min-w-11 min-h-11 flex items-center justify-center rounded-lg hover:bg-app-bg transition-colors z-10"
          title="Open Menu"
        >
          <Menu size={20} />
        </button>

        <div 
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-2 cursor-pointer select-none" 
          onClick={() => router.push(portal === "candidate" ? "/candidate/chat" : "/admin")}
        >
          {/* Logo icon */}
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-md shrink-0">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" opacity="0.9"/>
              <path d="M2 17L12 22L22 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M2 12L12 17L22 12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="flex items-baseline gap-0">
            <span className="text-app-text font-extrabold text-base tracking-tight">Vidyamarg</span>
            <span className="text-blue-600 dark:text-blue-400 font-extrabold text-base tracking-tight italic">AI</span>
          </div>
        </div>

        <button 
          onClick={toggleTheme}
          className="ml-auto text-app-text-muted hover:text-app-text p-2 min-w-11 min-h-11 flex items-center justify-center rounded-lg hover:bg-app-bg transition-colors z-10"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Moon size={20} className="text-slate-400" /> : <Sun size={20} className="text-amber-500" />}
        </button>
      </header>

      {/* Mobile Drawer Navigation overlay */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div 
            onClick={() => setMobileOpen(false)}
            className="fixed inset-0 bg-slate-950/40 dark:bg-black/60 backdrop-blur-xs transition-opacity duration-300"
          />

          {/* Drawer Menu Panel */}
          <aside className="relative flex flex-col w-64 max-w-xs h-full bg-app-surface border-r border-app-border transition-transform duration-300 ease-in-out z-50">
            {/* Header with Close */}
            <div className="flex-shrink-0 p-5 flex items-center justify-between">
              <div className="flex items-center gap-2 cursor-pointer" onClick={() => { setMobileOpen(false); router.push(portal === "candidate" ? "/candidate/chat" : "/admin"); }}>
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-md shrink-0">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" opacity="0.9"/>
                    <path d="M2 17L12 22L22 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <div className="flex items-baseline gap-0">
                  <span className="text-app-text font-extrabold text-base tracking-tight">Vidyamarg</span>
                  <span className="text-blue-600 dark:text-blue-400 font-extrabold text-base tracking-tight italic">AI</span>
                </div>
              </div>

              <button 
                onClick={() => setMobileOpen(false)}
                className="text-app-text-muted hover:text-app-text p-2 min-w-11 min-h-11 flex items-center justify-center rounded-lg hover:bg-app-bg transition-colors"
                title="Close Menu"
              >
                <X size={20} />
              </button>
            </div>

            {/* Scrollable Navigation Area */}
            <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-5 py-2">
              <nav className="flex flex-col gap-1.5">
                {activeLinks.map((link) => {
                  const Icon = link.icon;
                  const isActive = pathname === link.href || (link.href !== "/candidate/chat" && pathname.startsWith(link.href));
                  return (
                    <Link
                      key={link.name}
                      href={link.href}
                      onClick={() => setMobileOpen(false)}
                      aria-current={isActive ? "page" : undefined}
                      className={`flex items-center gap-3.5 px-4.5 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border ${
                        isActive
                          ? "bg-blue-50 dark:bg-blue-950/30 border-blue-200/60 dark:border-blue-800/30 text-blue-600 dark:text-blue-400"
                          : "text-app-text-secondary border-transparent hover:text-app-text hover:bg-slate-100/50 dark:hover:bg-slate-800/40"
                      }`}
                    >
                      <Icon size={18} className={`shrink-0 ${isActive ? "text-blue-600 dark:text-blue-400" : "text-app-text-muted"}`} />
                      <span>{link.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Footer */}
            <div className="flex-shrink-0 flex flex-col gap-3 p-5 border-t border-app-border bg-app-surface">
              {/* Theme Toggle */}
              <button 
                onClick={toggleTheme}
                className="flex items-center gap-3.5 w-full py-2.5 px-4.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer text-app-text-secondary hover:bg-slate-100/50 dark:hover:bg-slate-800/40"
              >
                {theme === "dark" ? (
                  <Moon size={18} className="text-slate-400 shrink-0" />
                ) : (
                  <Sun size={18} className="text-amber-500 shrink-0" />
                )}
                <span>{theme === "dark" ? "Dark Mode" : "Light Mode"}</span>
              </button>

              {/* User Profile Info */}
              <div className="flex items-center gap-2.5 py-2 px-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                <div 
                  onClick={() => { setMobileOpen(false); handleProfileClick(); }}
                  className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0 cursor-pointer hover:ring-2 hover:ring-blue-400/40 transition-all"
                >
                  {userInitial}
                </div>
                <div className="flex-1 min-w-0 overflow-hidden cursor-pointer" onClick={() => { setMobileOpen(false); handleProfileClick(); }}>
                  <h2 className="text-xs font-bold text-app-text truncate leading-tight">{displayName}</h2>
                  <span className="text-10 text-app-text-muted truncate block leading-tight">{displayEmail}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors cursor-pointer shrink-0"
                  title="Logout"
                >
                  <LogOut size={16} />
                </button>
              </div>
            </div>
          </aside>
        </div>
      )}

      {/* Desktop Sidebar (hidden on mobile) */}
      <aside className={`hidden md:flex ${collapsed ? "w-18" : "w-64"} h-screen border-r border-app-border bg-app-surface flex flex-col shrink-0 font-sans transition-all duration-300`}>
        {/* Header Logo — VidyamargAI */}
        <div className={`flex-shrink-0 flex flex-col gap-6 ${collapsed ? "p-3" : "p-5"}`}>
          <div className={`flex items-center ${collapsed ? "justify-center" : "justify-between"}`}>
            {!collapsed && (
              <div className="flex items-center gap-2 cursor-pointer" onClick={() => router.push(portal === "candidate" ? "/candidate/chat" : "/admin")}>
                {/* Logo icon */}
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-md shrink-0">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" opacity="0.9"/>
                    <path d="M2 17L12 22L22 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <div className="flex items-baseline gap-0">
                  <span className="text-app-text font-extrabold text-lg tracking-tight">Vidyamarg</span>
                  <span className="text-blue-600 dark:text-blue-400 font-extrabold text-lg tracking-tight italic">AI</span>
                </div>
              </div>
            )}
            <button 
              onClick={toggleCollapsed}
              className="text-app-text-muted hover:text-app-text p-1.5 min-w-11 min-h-11 flex items-center justify-center rounded-lg hover:bg-app-bg transition-colors"
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            </button>
          </div>
        </div>

        {/* Scrollable Navigation Area */}
        <div className={`flex-1 min-h-0 overflow-y-auto overflow-x-hidden ${collapsed ? "px-3" : "px-5"} py-2`}>
          <nav className="flex flex-col gap-1.5">
            {activeLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href || (link.href !== "/candidate/chat" && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.name}
                  href={link.href}
                  title={collapsed ? link.name : undefined}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex items-center ${collapsed ? "justify-center px-2" : "gap-3.5 px-4.5"} py-3 rounded-xl text-sm font-semibold transition-all duration-200 border ${
                    isActive
                      ? "bg-blue-50 dark:bg-blue-950/30 border-blue-200/60 dark:border-blue-800/30 text-blue-600 dark:text-blue-400"
                      : "text-app-text-secondary border-transparent hover:text-app-text hover:bg-slate-100/50 dark:hover:bg-slate-800/40"
                  }`}
                >
                  <Icon size={18} className={`shrink-0 ${isActive ? "text-blue-600 dark:text-blue-400" : "text-app-text-muted"}`} />
                  {!collapsed && <span>{link.name}</span>}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className={`flex-shrink-0 flex flex-col gap-3 ${collapsed ? "p-3" : "p-5"} border-t border-app-border bg-app-surface`}>

          {/* Theme Toggle */}
          <button 
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className={`flex items-center gap-3.5 w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer ${
              collapsed 
                ? "justify-center px-2 hover:bg-slate-100/50 dark:hover:bg-slate-800/40 text-app-text-secondary" 
                : "px-4.5 hover:bg-slate-100/50 dark:hover:bg-slate-800/40 text-app-text-secondary"
            }`}
          >
            {theme === "dark" ? (
              <Moon size={18} className="text-slate-400 shrink-0" />
            ) : (
              <Sun size={18} className="text-amber-500 shrink-0" />
            )}
            {!collapsed && (
              <span>{theme === "dark" ? "Dark Mode" : "Light Mode"}</span>
            )}
          </button>

          {/* User Profile + Logout — compact inline layout */}
          {collapsed ? (
            <div className="flex flex-col items-center gap-2">
              <div 
                onClick={handleProfileClick}
                className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0 cursor-pointer hover:ring-2 hover:ring-blue-400/40 transition-all"
                title={fullName || "Profile"}
              >
                {userInitial}
              </div>
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors cursor-pointer"
                title="Logout"
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2.5 py-2 px-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
              {/* Avatar */}
              <div 
                onClick={handleProfileClick}
                className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0 cursor-pointer hover:ring-2 hover:ring-blue-400/40 transition-all"
              >
                {userInitial}
              </div>
              {/* Name + Email */}
              <div className="flex-1 min-w-0 overflow-hidden cursor-pointer" onClick={handleProfileClick}>
                <h2 className="text-xs font-bold text-app-text truncate leading-tight">{displayName}</h2>
                <span className="text-10 text-app-text-muted truncate block leading-tight">{displayEmail}</span>
              </div>
              {/* Logout icon */}
              <button
                onClick={handleLogout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors cursor-pointer shrink-0"
                title="Logout"
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </aside>
      {/* Mobile Bottom Navigation Bar for Candidate (Mobile view only) */}
      {portal === "candidate" && (
        <nav
          className="sm:hidden fixed bottom-0 left-0 right-0 z-40 bg-app-surface border-t border-app-border flex justify-around items-center px-2 w-full font-sans shadow-[0_-2px_10px_rgba(0,0,0,0.05)] dark:shadow-[0_-2px_10px_rgba(0,0,0,0.2)]"
          style={{ paddingBottom: "max(16px, env(safe-area-inset-bottom, 16px))", height: "calc(64px + env(safe-area-inset-bottom, 0px))" }}
        >
          {[
            { name: "Resume", href: "/candidate/resume", icon: FileText },
            { name: "Skill Lab", href: "/candidate/skill-lab", icon: Compass },
            { name: "Ask Tush AI", href: "/candidate/chat", icon: Sparkles },
            { name: "Profile", href: "/candidate/profile", icon: Users }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = pathname === tab.href || (tab.href !== "/candidate/chat" && pathname.startsWith(tab.href));
            return (
              <Link
                key={tab.name}
                href={tab.href}
                aria-current={isActive ? "page" : undefined}
                className={`flex flex-col items-center justify-center flex-1 py-1 transition-all ${
                  isActive
                    ? "text-blue-600 dark:text-blue-400"
                    : "text-app-text-muted hover:text-app-text"
                }`}
              >
                <Icon size={20} className="mb-0.5 shrink-0" />
                <span className="text-10 font-semibold tracking-tight leading-none">{tab.name}</span>
              </Link>
            );
          })}
        </nav>
      )}
    </>
  );
}
