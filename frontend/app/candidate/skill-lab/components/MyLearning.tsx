"use client";


interface MyLearningProps {
  enrollments: any[];
  courses: any[];
  handleStartCourse: (course: any) => Promise<void>;
  setActiveView: (view: any) => void;
}

export default function MyLearning({
  enrollments,
  courses,
  handleStartCourse,
  setActiveView
}: MyLearningProps) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-black text-slate-905 dark:text-white leading-tight">My Learning</h2>
        <p className="text-xs text-slate-500 mt-1 font-medium">Track your ongoing courses, progress, and upcoming assessments</p>
      </div>

      {enrollments.length > 0 ? (
        <div className="flex flex-col gap-6">
          {enrollments.map((enroll) => {
            const courseObj = courses.find(c => c.id === enroll.course_id) || enroll.course;
            if (!courseObj) return null;
            
            const nextAssessmentType = enroll.progress >= 100 
              ? "All Completed! Claim Certificate"
              : "Module 1 Assessment";

            return (
              <div 
                key={enroll.id} 
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-850 rounded-3xl p-6 shadow-sm flex flex-col gap-5"
              >
                <div className="flex justify-between items-start border-b border-slate-100 dark:border-slate-800/40 pb-4">
                  <div>
                    <span className="px-2 py-0.5 rounded text-8 font-bold font-mono bg-indigo-100 text-indigo-650 dark:bg-indigo-950/30 dark:text-indigo-400 uppercase tracking-wider">
                      Active Course
                    </span>
                    <h3 className="text-base font-black text-slate-800 dark:text-white mt-2 leading-snug">{courseObj.title}</h3>
                    <span className="text-10 text-slate-500 mt-1 block font-medium">Instructor: {courseObj.instructor}</span>
                  </div>
                  
                  <div className="text-right">
                    <span className="text-sm font-black text-emerald-500 block">{Math.round(enroll.progress)}% Complete</span>
                    <span className="text-9 text-slate-400 font-bold block mt-0.5">Overall Progress</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl">
                    <span className="text-9 uppercase font-bold text-slate-400">Current Module</span>
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300 block mt-1.5 truncate">
                      Module 1
                    </span>
                  </div>

                  <div className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl">
                    <span className="text-9 uppercase font-bold text-slate-400">Next Assessment</span>
                    <span className="text-xs font-bold text-indigo-650 dark:text-indigo-400 block mt-1.5 font-sans">
                      {nextAssessmentType}
                    </span>
                  </div>

                  <div className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl flex items-center justify-between">
                    <div>
                      <span className="text-9 uppercase font-bold text-slate-400">Status</span>
                      <span className="text-xs font-bold text-slate-700 dark:text-slate-300 block mt-1.5 capitalize">{enroll.status}</span>
                    </div>
                    
                    <button
                      onClick={async () => {
                        await handleStartCourse(courseObj);
                      }}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl transition-all cursor-pointer shadow-sm"
                    >
                      Resume Learning
                    </button>
                  </div>
                </div>

                <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-600 transition-all duration-500" style={{ width: `${enroll.progress}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 border-dashed rounded-3xl p-12 text-center flex flex-col items-center justify-center gap-3">
          <p className="text-xs text-slate-500 font-bold">You are not enrolled in any learning paths yet.</p>
          <button 
            onClick={() => setActiveView("explore")}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl transition-all cursor-pointer"
          >
            Browse Courses
          </button>
        </div>
      )}
    </div>
  );
}
