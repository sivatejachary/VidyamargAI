"use client";

import { CareerPath, PATH_BADGES } from "@/types/lms.types";
import { ArrowRight, Clock, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

/* ═══════════════════════════════════════════════════════
   CareerPathCard — Primary navigation card for goal-based
   learning discovery. Google Career Certificate style.
   ═══════════════════════════════════════════════════════ */

interface CareerPathCardProps {
  path: CareerPath;
  onViewPath?: (path: CareerPath) => void;
}

export default function CareerPathCard({ path, onViewPath }: CareerPathCardProps) {
  const badgeConfig = path.badge ? PATH_BADGES[path.badge] : null;

  return (
    <button
      type="button"
      aria-label={`View ${path.title} career path`}
      onClick={() => onViewPath?.(path)}
      className={`relative bg-gradient-to-br ${path.gradient} rounded-2xl overflow-hidden w-full h-full text-left cursor-pointer group transition-all duration-200 hover:-translate-y-1 hover:shadow-xl motion-reduce:hover:transform-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring`}
    >
      {/* Glass overlay for depth */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/0 via-black/5 to-black/20 pointer-events-none" />

      <div className="relative p-5 flex flex-col justify-between min-h-[220px] h-full gap-3">
        {/* Top: Badge + Icon */}
        <div className="flex items-start justify-between">
          <span className="text-3xl" role="img" aria-hidden="true">
            {path.icon}
          </span>
          {badgeConfig && (
            <span className="text-[11px] font-bold bg-white/25 backdrop-blur-sm text-white px-2.5 py-1 rounded-lg">
              {badgeConfig.label}
            </span>
          )}
        </div>

        {/* Middle: Title + Subtitle */}
        <div className="flex-1 flex flex-col justify-center">
          <h3 className="text-base font-bold text-white leading-snug">
            {path.title}
          </h3>
          <p className="text-xs text-white/65 mt-1 leading-relaxed line-clamp-2">
            {path.subtitle}
          </p>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-3 text-white/70">
          <span className="flex items-center gap-1 text-xs">
            <BookOpen size={12} />
            {path.courseCount} courses
          </span>
          <span className="w-px h-3 bg-white/30" />
          <span className="flex items-center gap-1 text-xs">
            <Clock size={12} />
            {path.totalHours}h
          </span>
        </div>

        {/* Skills preview */}
        <div className="flex flex-wrap gap-1.5">
          {path.skills.slice(0, 3).map((skill) => (
            <span
              key={skill}
              className="bg-white/15 text-white text-[10px] font-medium px-2 py-0.5 rounded-md"
            >
              {skill}
            </span>
          ))}
          {path.skills.length > 3 && (
            <span className="text-white/50 text-[10px] font-medium px-1 py-0.5">
              +{path.skills.length - 3}
            </span>
          )}
        </div>

        {/* CTA */}
        <div className="flex items-center gap-1.5 text-sm font-semibold text-white group-hover:gap-2.5 transition-all duration-200">
          Explore Path
          <ArrowRight size={14} className="transition-transform duration-200 group-hover:translate-x-1" />
        </div>
      </div>
    </button>
  );
}
