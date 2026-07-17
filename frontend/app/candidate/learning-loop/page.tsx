'use client';

import { useState } from 'react';

const COACHING_PLANS = [
  {
    stage_failed: 'Resume Screening',
    icon: '📄',
    weaknesses: ['Resume formatting issues', 'Missing quantifiable achievements', 'Skills not aligned with JD', 'Weak professional summary'],
    actions: [
      { type: 'Tool', label: 'AI Resume Review', link: '/candidate/resume-review', icon: '🤖' },
      { type: 'Tool', label: 'Rebuild Resume with AI', link: '/candidate/resume-builder', icon: '✏️' },
      { type: 'Course', label: 'Resume Writing Masterclass', link: '/candidate/learning', icon: '📚' },
    ],
    tips: ['Add specific metrics (e.g. "Improved performance by 40%")', 'Mirror keywords from the job description', 'Use strong action verbs', 'Keep to 1 page if under 5 years experience'],
  },
  {
    stage_failed: 'MCQ Assessment',
    icon: '📝',
    weaknesses: ['Knowledge gaps in core areas', 'Poor time management under pressure', 'Insufficient MCQ practice', 'Rushing through questions'],
    actions: [
      { type: 'Practice', label: 'Take 50 Practice MCQs', link: '/candidate/mock-mcq', icon: '📝' },
      { type: 'Course', label: 'Subject Knowledge Deep-Dive', link: '/candidate/learning', icon: '📚' },
      { type: 'AI', label: 'AI Study Plan', link: '/candidate/ai-mentor', icon: '🤖' },
    ],
    tips: ['Practice 30+ MCQs daily for 7 days', 'Study core concepts, not just memorization', 'Max 90 seconds per question', 'Review wrong answer explanations'],
  },
  {
    stage_failed: 'Coding Assessment',
    icon: '💻',
    weaknesses: ['Algorithm complexity issues', 'Unfamiliarity with data structures', 'Unoptimized solutions', 'Edge cases not handled'],
    actions: [
      { type: 'Practice', label: 'Practice Coding Problems', link: '/candidate/mock-coding', icon: '💻' },
      { type: 'Course', label: 'DSA Masterclass', link: '/candidate/learning', icon: '📚' },
      { type: 'AI', label: 'AI Code Review', link: '/candidate/ai-mentor', icon: '🤖' },
    ],
    tips: ['Practice 2-3 coding problems daily', 'Master Arrays, HashMaps, Trees, Graphs', 'Always handle edge cases: empty, null, overflow', 'Write clean commented code'],
  },
];

export default function LearningLoopPage() {
  const [selectedPlan, setSelectedPlan] = useState(COACHING_PLANS[0]);
  const [animating, setAnimating] = useState(false);

  const switchPlan = (plan: typeof COACHING_PLANS[0]) => {
    setAnimating(true);
    setTimeout(() => { setSelectedPlan(plan); setAnimating(false); }, 200);
  };

  return (
    <div className="min-h-screen bg-[#05060f] text-white">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_rgba(109,40,217,0.10),_transparent_60%),radial-gradient(ellipse_at_bottom_right,_rgba(239,68,68,0.06),_transparent_50%)]" />
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-rose-600 to-orange-600">
              <span className="text-xl">🔄</span>
            </div>
            <h1 className="text-2xl font-black">AI Personalized Coaching Hub</h1>
          </div>
          <p className="text-slate-400 text-sm">Your AI coach has analyzed your performance and created a personalized recovery plan.</p>
        </div>

        <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
          {COACHING_PLANS.map(plan => (
            <button key={plan.stage_failed} onClick={() => switchPlan(plan)}
              className={`flex-shrink-0 flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition-all ${
                selectedPlan.stage_failed === plan.stage_failed
                  ? 'border-violet-500/50 bg-violet-500/10 text-white'
                  : 'border-white/8 bg-white/3 text-slate-400 hover:border-white/15 hover:text-white'
              }`}>
              <span>{plan.icon}</span> <span>{plan.stage_failed}</span>
            </button>
          ))}
        </div>

        <div className={`transition-opacity duration-200 ${animating ? 'opacity-0' : 'opacity-100'}`}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-4">
              <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-5">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{selectedPlan.icon}</span>
                  <div>
                    <h2 className="text-base font-bold text-white">Weakness Analysis</h2>
                    <p className="text-xs text-rose-400">Failed: {selectedPlan.stage_failed}</p>
                  </div>
                </div>
                <ul className="space-y-2">
                  {selectedPlan.weaknesses.map((w, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="text-rose-400 mt-0.5 flex-shrink-0">⚠</span>{w}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5">
                <h3 className="text-sm font-bold text-amber-400 mb-3">💡 AI Coach Tips</h3>
                <ul className="space-y-2">
                  {selectedPlan.tips.map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                      <span className="text-amber-400 flex-shrink-0">{i + 1}.</span>{tip}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              <div className="rounded-2xl border border-white/8 bg-white/2 p-6">
                <h2 className="text-base font-bold text-white mb-4">🎯 Your Recovery Action Plan</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {selectedPlan.actions.map((action, i) => (
                    <a key={i} href={action.link} className="group relative overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4 hover:border-violet-500/30 hover:bg-violet-500/5 transition-all duration-200">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl">{action.icon}</span>
                        <span className="text-xs font-bold text-slate-400 uppercase">{action.type}</span>
                      </div>
                      <p className="text-sm font-semibold text-white group-hover:text-violet-300 transition">{action.label}</p>
                      <div className="mt-3 flex items-center gap-1 text-xs text-violet-400 font-medium">
                        Start Now <span className="group-hover:translate-x-1 transition-transform">→</span>
                      </div>
                    </a>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6">
                <h2 className="text-base font-bold text-white mb-4">📅 7-Day Recovery Schedule</h2>
                <div className="grid grid-cols-7 gap-2">
                  {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((day, i) => (
                    <div key={day} className="text-center">
                      <p className="text-[10px] text-slate-500 mb-1.5 font-bold uppercase">{day}</p>
                      <div className={`rounded-xl border p-2 text-center ${
                        i < 5 ? 'border-emerald-500/25 bg-emerald-500/10' : 'border-blue-500/25 bg-blue-500/10'
                      }`}>
                        <span className="text-xs">{i < 5 ? '📚' : '🧘'}</span>
                        <p className="text-[9px] text-slate-400 mt-0.5 leading-tight">{i < 5 ? 'Study + Practice' : 'Review & Rest'}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-violet-500/25 bg-gradient-to-br from-violet-500/10 to-indigo-500/10 p-6 text-center">
                <h3 className="text-lg font-bold text-white mb-1">Ready to Try Again?</h3>
                <p className="text-sm text-slate-400 mb-4">Complete your coaching plan and reapply with confidence.</p>
                <a href="/candidate/job-agent?tab=feed" className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 px-6 py-3 text-sm font-bold text-white transition-all shadow-lg shadow-violet-500/20">
                  🚀 Browse Jobs & Reapply
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
