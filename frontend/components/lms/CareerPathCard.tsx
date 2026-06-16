"use client";

import { CareerPath } from "@/types/lms.types";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

interface CareerPathCardProps {
  path: CareerPath;
  onViewPath?: (path: CareerPath) => void;
}

export default function CareerPathCard({ path, onViewPath }: CareerPathCardProps) {
  const displayedSkills = path.skills.slice(0, 3);

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
      className={`relative bg-gradient-to-br ${path.gradient} rounded-2xl overflow-hidden h-full cursor-default`}
      style={{ willChange: "transform" }}
    >
      {/* Subtle overlay for depth */}
      <div className="absolute inset-0 bg-black/10 pointer-events-none" />

      <div className="relative p-6 flex flex-col justify-between min-h-[180px] h-full">
        {/* Top — Title */}
        <div>
          <h3 className="text-lg font-bold text-white">{path.title}</h3>

          {/* Middle — Stats */}
          <p className="mt-1 text-sm text-white/70">
            {path.courseCount} courses · {path.totalHours} hours
          </p>
        </div>

        {/* Skills row */}
        <div className="flex flex-wrap gap-2 mt-4">
          {displayedSkills.map((skill) => (
            <span
              key={skill}
              className="bg-white/20 text-white text-xs px-2.5 py-1 rounded-full"
            >
              {skill}
            </span>
          ))}
        </div>

        {/* Bottom — View Path button */}
        <button
          type="button"
          aria-label={`View career path: ${path.title}`}
          onClick={() => onViewPath?.(path)}
          className="mt-4 inline-flex items-center gap-1.5 bg-white/20 hover:bg-white/30 text-white rounded-xl px-4 py-2 text-sm font-semibold cursor-pointer transition-colors duration-200 w-fit"
        >
          View Path
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}
