"use client";

import React, { useRef } from "react";
import { motion } from "framer-motion";
import { 
  Search, 
  FileText, 
  CheckSquare, 
  Map, 
  Cpu, 
  Video, 
  MessageSquareCode, 
  DollarSign, 
  Building2, 
  BarChart, 
  Award, 
  Layout 
} from "lucide-react";

const features = [
  {
    title: "AI Job Discovery",
    desc: "Scan the market dynamically based on your detailed candidate profile and skill matches.",
    icon: Search,
    color: "from-purple-500/20 to-indigo-500/5",
    border: "group-hover:border-purple-500/40"
  },
  {
    title: "Resume Builder",
    desc: "Input your career experience and construct beautiful, professional templates in minutes.",
    icon: FileText,
    color: "from-blue-500/20 to-indigo-500/5",
    border: "group-hover:border-blue-500/40"
  },
  {
    title: "ATS Resume Score",
    desc: "Receive real-time checks on formatting, word repetitions, and keywords alignment.",
    icon: CheckSquare,
    color: "from-cyan-500/20 to-indigo-500/5",
    border: "group-hover:border-cyan-500/40"
  },
  {
    title: "Skill Gap Analysis",
    desc: "Visually cross-examine your skills against dream jobs to uncover critical gaps.",
    icon: Map,
    color: "from-purple-500/20 to-pink-500/5",
    border: "group-hover:border-purple-500/40"
  },
  {
    title: "Personalized Learning Roadmaps",
    desc: "AI builds a custom learning path with integrated courses to fill missing competencies.",
    icon: Cpu,
    color: "from-emerald-500/20 to-indigo-500/5",
    border: "group-hover:border-emerald-500/40"
  },
  {
    title: "AI Mock Interviews",
    desc: "Practice behavioral and tech rounds with an interactive interviewer scoring your responses.",
    icon: Video,
    color: "from-amber-500/20 to-orange-500/5",
    border: "group-hover:border-amber-500/40"
  },
  {
    title: "Career Coach",
    desc: "Chat with a 24/7 autonomous career mentor regarding job negotiations or study path choice.",
    icon: MessageSquareCode,
    color: "from-indigo-500/20 to-purple-500/5",
    border: "group-hover:border-indigo-500/40"
  },
  {
    title: "Salary Insights",
    desc: "Gain transparent, real-world data regarding roles, geographic regions, and seniority tiers.",
    icon: DollarSign,
    color: "from-rose-500/20 to-pink-500/5",
    border: "group-hover:border-rose-500/40"
  },
  {
    title: "Company Insights",
    desc: "Access historical interview question pools and culture indexes for prospective companies.",
    icon: Building2,
    color: "from-blue-500/20 to-cyan-500/5",
    border: "group-hover:border-blue-500/40"
  },
  {
    title: "Career Analytics",
    desc: "Track application success rates, interview volumes, and skill badges in real-time.",
    icon: BarChart,
    color: "from-violet-500/20 to-purple-500/5",
    border: "group-hover:border-violet-500/40"
  },
  {
    title: "Certifications",
    desc: "Unlock verifiable career completion badges for your resume as you master courses.",
    icon: Award,
    color: "from-emerald-500/20 to-teal-500/5",
    border: "group-hover:border-emerald-500/40"
  },
  {
    title: "Personalized Dashboard",
    desc: "A beautiful cockpit to manage applications, schedule calls, and track course accomplishments.",
    icon: Layout,
    color: "from-pink-500/20 to-purple-500/5",
    border: "group-hover:border-pink-500/40"
  }
];

export default function Features() {
  
  // Custom 3D Tilt calculation
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Convert to rotation coordinates (-6 to 6 degrees)
    const rotX = -((y / rect.height) - 0.5) * 12;
    const rotY = ((x / rect.width) - 0.5) * 12;
    
    card.style.transform = `perspective(1000px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale3d(1.02, 1.02, 1.02) translateY(-6px)`;
    card.style.borderColor = "rgba(168, 85, 247, 0.4)";
    card.style.boxShadow = "0 15px 30px rgba(147, 51, 234, 0.1)";
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget;
    card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1) translateY(0px)";
    card.style.borderColor = "rgba(38, 38, 38, 0.8)";
    card.style.boxShadow = "none";
  };

  return (
    <section id="features" className="py-24 relative overflow-hidden z-10">
      
      {/* Background soft lighting blobs */}
      <div className="absolute top-1/4 right-1/4 w-80 h-80 bg-purple-600/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-80 h-80 bg-blue-600/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Everything You Need to <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Launch Your Career</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Twelve advanced modules engineered specifically to build, target, and accelerate your career.
          </p>
        </div>

        {/* FEATURES GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 select-none">
          {features.map((feature, idx) => {
            const IconComponent = feature.icon;

            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, delay: (idx % 4) * 0.1 }}
                className="w-full shrink-0 select-none group"
              >
                <div
                  onMouseMove={handleMouseMove}
                  onMouseLeave={handleMouseLeave}
                  className="h-full p-6 rounded-2xl border border-slate-900 bg-slate-950/40 backdrop-blur-md transition-all duration-300 light-sweep-container flex flex-col justify-between select-none"
                  style={{ transitionProperty: "background, border-color, box-shadow" }}
                >
                  <div className="flex flex-col gap-4 relative z-10 pointer-events-none">
                    
                    {/* Glowing Accent Circle behind icon */}
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center border border-white/5`}>
                      <IconComponent className="w-5 h-5 text-slate-300 group-hover:text-white transition-colors" />
                    </div>

                    <h3 className="font-heading font-bold text-base text-white group-hover:text-purple-300 transition-colors">
                      {feature.title}
                    </h3>
                    
                    <p className="font-sans text-xs text-slate-500 leading-relaxed">
                      {feature.desc}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
