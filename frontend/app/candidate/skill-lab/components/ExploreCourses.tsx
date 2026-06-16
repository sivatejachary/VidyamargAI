"use client";

import { 
  Star, Clock, BookOpen, Brain, Play, CheckCircle, Code, Terminal, Compass, BarChart3, Search, ShieldCheck, Award
} from "lucide-react";

const GRADIENT_CLASSES = [
  "from-blue-600 to-indigo-700",
  "from-violet-600 to-fuchsia-700",
  "from-emerald-500 to-teal-700",
  "from-orange-500 to-amber-600",
  "from-pink-500 to-rose-600"
];

interface ExploreCoursesProps {
  courses: any[];
  enrollments: any[];
  enrolledCourseIds: any[];
  readinessScore: number;
  activeView: string;
  setActiveView: (view: any) => void;
  selectedCourse: any;
  setSelectedCourse: (course: any) => void;
  activeEnrollmentCourse: any;
  activeEnrollmentCurriculum: any;
  handleStartCourse: (course: any) => Promise<void>;
  handleGoToLesson: (course: any, type: string) => Promise<void>;
  completedLessonIds: number[];
  
  // Shared states from parent
  courseSearchQuery: string;
  setCourseSearchQuery: (val: string) => void;
  courseCategoryFilter: string;
  setCourseCategoryFilter: (val: string) => void;
  showAllCourses: boolean;
  setShowAllCourses: (val: boolean) => void;
}

export default function ExploreCourses({
  courses,
  enrollments,
  enrolledCourseIds,
  readinessScore,
  activeView,
  setActiveView,
  selectedCourse,
  setSelectedCourse,
  activeEnrollmentCourse,
  activeEnrollmentCurriculum,
  handleStartCourse,
  handleGoToLesson,
  completedLessonIds,
  courseSearchQuery,
  setCourseSearchQuery,
  courseCategoryFilter,
  setCourseCategoryFilter,
  showAllCourses,
  setShowAllCourses
}: ExploreCoursesProps) {
  const activeCourses = courses;
  
  // Extract unique categories dynamically from actual courses
  const categories = Array.from(new Set(activeCourses.map((c: any) => c.category))).filter(Boolean);

  const filteredCourses = activeCourses.filter((c: any) => {
    const matchesSearch = !courseSearchQuery || 
      c.title?.toLowerCase().includes(courseSearchQuery.toLowerCase()) ||
      c.instructor?.toLowerCase().includes(courseSearchQuery.toLowerCase()) ||
      c.category?.toLowerCase().includes(courseSearchQuery.toLowerCase());
    const matchesCategory = courseCategoryFilter === "All" || 
      c.category?.toLowerCase().includes(courseCategoryFilter.toLowerCase());
    return matchesSearch && matchesCategory;
  });

  const renderCourseCard = (c: any) => {
    const enrolled = enrolledCourseIds.includes(c.id);
    const modulesCount = c.totalModules || c.modules || 0;
    
    const courseIdx = activeCourses.findIndex(ac => ac.id === c.id);
    const gradientClass = GRADIENT_CLASSES[courseIdx >= 0 ? courseIdx % GRADIENT_CLASSES.length : 0];

    return (
      <div 
        key={c.id}
        className="bg-card border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden hover:border-slate-350 dark:hover:border-slate-700 hover:scale-[1.02] hover:shadow-md transition-all duration-300 flex flex-col justify-between h-390 relative group"
      >
        {/* Course Thumbnail placeholder with subtle gradient & icon */}
        <div className={`h-40 w-full bg-gradient-to-br ${gradientClass} flex items-center justify-center relative`}>
          <div className="absolute inset-0 bg-black/5" />
          <Brain size={44} className="text-white/40 drop-shadow" />
          <span className="absolute bottom-3 left-3 px-2 py-0.8 rounded bg-black/45 backdrop-blur-md text-9 font-black text-white uppercase tracking-wider">
            {c.tag || c.category}
          </span>
        </div>

        {/* Content details */}
        <div className="p-4 flex-1 flex flex-col justify-between">
          <div className="flex flex-col gap-1.5">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-snug line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              {c.title}
            </h4>
            <span className="text-xs text-slate-500 dark:text-slate-450 font-medium">{c.instructor}</span>
            
            {/* Rating */}
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-xs font-extrabold text-amber-600 dark:text-amber-500">{c.rating}</span>
              <div className="flex items-center gap-0.5">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={11} className={`${i < Math.floor(c.rating || 4.5) ? 'text-amber-550 fill-amber-550' : 'text-slate-300 dark:text-slate-700'}`} />
                ))}
              </div>
              <span className="text-10 text-slate-400 dark:text-slate-500">({courseIdx * 12 + 45})</span>
            </div>
          </div>

          <div className="border-t border-slate-100 dark:border-slate-800/60 pt-3 mt-4 flex items-center justify-between">
            <div className="flex flex-col gap-0.5 text-slate-450 dark:text-slate-500 text-10 font-bold">
              <span className="flex items-center gap-1">
                <Clock size={11} /> {c.duration || "12 Hours"}
              </span>
              <span className="flex items-center gap-1">
                <BookOpen size={11} /> {modulesCount} Modules
              </span>
            </div>

            <button
              onClick={async (e) => {
                e.stopPropagation();
                await handleStartCourse(c);
              }}
              className={`px-4 py-2 text-xs font-bold rounded-xl transition-all cursor-pointer shadow-sm border ${
                enrolled
                  ? "bg-transparent border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-700 dark:text-slate-300"
                  : "bg-black dark:bg-white text-white dark:text-black border-transparent hover:opacity-90"
              }`}
            >
              {enrolled ? "Resume" : "Enroll"}
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderContinueLearningStepper = (enroll: any, courseObj: any) => {
    const targetCourse = courseObj || activeCourses[0];
    const progressPercent = enroll ? Math.round(enroll.progress) : 0;
    
    let totalModulesCount = targetCourse?.totalModules || targetCourse?.modules || 3;
    let completedModulesCount = Math.round((progressPercent / 100) * totalModulesCount);

    return (
      <div key={enroll?.id || enroll?.course_id || targetCourse?.id} className="bg-card border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm hover:scale-[1.01] hover:shadow-md transition-all duration-300 flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden w-full">
        <div className="flex items-center gap-4 flex-1 w-full">
          {/* Small clean course icon area instead of huge image */}
          <div className="w-14 h-14 rounded-xl bg-blue-50 dark:bg-blue-950/30 flex items-center justify-center shrink-0 shadow-inner">
            <Brain size={26} className="text-blue-650 dark:text-blue-400" />
          </div>

          <div className="flex-1 min-w-0">
            <span className="text-10 font-black text-blue-600 dark:text-blue-400 uppercase tracking-wider">Continue Learning</span>
            <h3 className="text-base font-extrabold text-slate-950 dark:text-white mt-0.5 truncate leading-snug">{targetCourse?.title || "Course"}</h3>
            <p className="text-xs text-slate-505 dark:text-slate-400 font-medium truncate">{targetCourse?.instructor || "Jose Portilla"}</p>
          </div>
        </div>

        {/* Clean Progress Section */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-6 w-full md:w-auto shrink-0 border-t md:border-t-0 border-slate-100 dark:border-slate-800/40 pt-4 md:pt-0">
          <div className="flex flex-col gap-1 w-full sm:w-44">
            <div className="flex items-center justify-between text-xs font-bold">
              <span className="text-slate-505 dark:text-slate-400">{completedModulesCount} / {totalModulesCount} Modules Completed</span>
              <span className="text-blue-600 dark:text-blue-400 font-black">{progressPercent}% Complete</span>
            </div>
            <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-blue-600 dark:bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${progressPercent}%` }} />
            </div>
          </div>

          <button
            onClick={() => handleGoToLesson(targetCourse, "video")}
            className="px-5 py-3 bg-black dark:bg-white text-white dark:text-black font-semibold text-xs rounded-xl hover:opacity-90 transition-all cursor-pointer shadow-sm flex items-center justify-center gap-2"
          >
            <Play size={12} className="fill-current shrink-0" />
            <span>Resume Learning</span>
          </button>
        </div>
      </div>
    );
  };

  if (activeView === "explore") {
    return (
      <div className="flex flex-col gap-8 w-full">
        {!showAllCourses && enrollments.length > 0 && (
          <div className="flex flex-col gap-4">
            {enrollments.map((enroll) => {
              const courseObj = courses.find(c => c.id === enroll.course_id) || enroll.course;
              return renderContinueLearningStepper(enroll, courseObj);
            })}
          </div>
        )}

        {showAllCourses ? (
          <div className="flex flex-col gap-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-black text-slate-800 dark:text-white">All Courses ({filteredCourses.length})</h3>
              <button 
                onClick={() => { setShowAllCourses(false); setCourseCategoryFilter("All"); setCourseSearchQuery(""); }}
                className="text-xs font-bold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 cursor-pointer"
              >
                ← Back to Explore
              </button>
            </div>

            <div className="flex flex-wrap gap-3 items-center">
              <div className="relative flex-1 min-w-200">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-450 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search courses by title, instructor, or category..."
                  value={courseSearchQuery}
                  onChange={(e) => setCourseSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900 text-xs text-slate-800 dark:text-slate-150 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {["All", ...categories].map((cat: any) => (
                  <button
                    key={cat}
                    onClick={() => setCourseCategoryFilter(cat)}
                    className={`px-3.5 py-2 rounded-xl text-10 font-bold border transition-all cursor-pointer ${
                      courseCategoryFilter === cat
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800 hover:border-indigo-500/40"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {filteredCourses.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredCourses.map((c: any) => renderCourseCard(c))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                <p className="text-sm font-semibold">No courses found matching your filters.</p>
                <button 
                  onClick={() => { setCourseCategoryFilter("All"); setCourseSearchQuery(""); }}
                  className="text-xs text-indigo-600 dark:text-indigo-400 font-bold mt-2 cursor-pointer hover:underline"
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center w-full">
                <h3 className="text-base font-black text-slate-800 dark:text-white">Recommended for You</h3>
                <button 
                  onClick={() => setShowAllCourses(true)} 
                  className="text-xs font-bold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 cursor-pointer"
                >
                  View All
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {activeCourses.slice(0, 3).map((c) => renderCourseCard(c))}
              </div>
            </div>

            {activeCourses.length > 3 && (
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center w-full">
                  <h3 className="text-base font-black text-slate-800 dark:text-white">More Courses</h3>
                  <button 
                    onClick={() => setShowAllCourses(true)} 
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 cursor-pointer"
                  >
                    View All ({activeCourses.length})
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {activeCourses.slice(3, 6).map((c) => renderCourseCard(c))}
                </div>
              </div>
            )}

            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center w-full">
                <h3 className="text-base font-black text-slate-800 dark:text-white">Popular Categories</h3>
              </div>

              <div className="flex flex-wrap items-center gap-3 w-full">
                {[
                  { label: "AI & Machine Learning", icon: Brain, color: "bg-purple-100 text-purple-600 dark:bg-purple-950/30 dark:text-purple-400", value: "Machine Learning" },
                  { label: "Programming", icon: Code, color: "bg-blue-100 text-blue-600 dark:bg-blue-950/30 dark:text-blue-400", value: "Programming" },
                  { label: "System Design", icon: BarChart3, color: "bg-teal-100 text-teal-600 dark:bg-teal-950/30 dark:text-teal-400", value: "System Design" },
                  { label: "Cloud Computing", icon: ShieldCheck, color: "bg-sky-100 text-sky-600 dark:bg-sky-950/30 dark:text-sky-400", value: "Cloud Computing" },
                  { label: "Web Development", icon: Terminal, color: "bg-orange-100 text-orange-600 dark:bg-orange-950/30 dark:text-orange-400", value: "Web Development" },
                  { label: "Mobile Development", icon: Compass, color: "bg-pink-100 text-pink-600 dark:bg-pink-950/30 dark:text-pink-400", value: "Mobile Development" },
                  { label: "Database", icon: Code, color: "bg-emerald-100 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400", value: "Database" }
                ].map((cat, i) => {
                  const Icon = cat.icon;
                  return (
                    <button
                      key={i}
                      onClick={() => {
                        setCourseCategoryFilter(cat.value);
                        setShowAllCourses(true);
                      }}
                      className="flex items-center gap-3 px-4.5 py-2.8 rounded-2xl border text-xs font-black transition-all cursor-pointer bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800/80 hover:border-indigo-500/35 hover:shadow-sm"
                    >
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${cat.color}`}>
                        <Icon size={14} className="shrink-0" />
                      </div>
                      <span className="text-slate-700 dark:text-slate-300">{cat.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  if (activeView === "course-details" && selectedCourse) {
    return (
      <div className="flex flex-col gap-6">
        <button 
          onClick={() => setActiveView("explore")}
          className="self-start text-10 font-bold text-indigo-600 hover:underline flex items-center gap-1 cursor-pointer"
        >
          <span>← Back to Catalog</span>
        </button>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm flex flex-col md:flex-row items-stretch">
          <div className="md:w-56 bg-gradient-to-tr from-indigo-500/20 to-teal-500/20 flex items-center justify-center p-8 shrink-0 min-h-160">
            <Brain size={48} className="text-indigo-500/50" />
          </div>
          
          <div className="p-6 flex-1 flex flex-col justify-between gap-4">
            <div>
              <span className="text-9 font-mono font-bold px-2 py-0.5 bg-indigo-100 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400 rounded uppercase">
                {selectedCourse.tag || selectedCourse.category}
              </span>
              <h2 className="text-xl font-black text-slate-800 dark:text-white mt-2.5 leading-snug">{selectedCourse.title}</h2>
              <p className="text-xs text-slate-500 mt-1">Instructor: <span className="font-bold text-slate-700 dark:text-slate-350">{selectedCourse.instructor}</span></p>
              
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-3 leading-relaxed">
                {selectedCourse.description || "Learn core fundamentals, best practices, scaling techniques, and complete practical projects with verifiable certificates."}
              </p>
            </div>

            <div className="border-t border-slate-100 dark:border-slate-800/40 pt-4 flex flex-wrap gap-4 items-center justify-between">
              <div className="flex gap-4 text-10 text-slate-450 font-bold">
                <span className="flex items-center gap-1"><Star size={12} className="text-amber-500 fill-amber-500" /> {selectedCourse.rating}</span>
                <span>•</span>
                <span className="flex items-center gap-1"><Clock size={12} /> {selectedCourse.duration || "12 Hours"}</span>
                <span>•</span>
                <span className="flex items-center gap-1"><Award size={12} className="text-teal-500" /> Certificate Included</span>
              </div>

              <button
                onClick={async () => {
                  await handleStartCourse(selectedCourse);
                }}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-755 text-white text-xs font-bold rounded-xl transition-all cursor-pointer shadow-md"
              >
                {enrolledCourseIds.includes(selectedCourse.id) ? "Resume Class Player" : "Enroll & Start Course"}
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">What You'll Learn</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs text-slate-600 dark:text-slate-400 leading-normal">
            {[
              `Complete ${selectedCourse.title} curriculum`,
              `Hands-on quizzes, written assessments & AI interviews`,
              `Industry-relevant practical skills`,
              `Earn a verified certificate on completion`
            ].map((learn: string, i: number) => (
              <div key={i} className="flex gap-2.5 items-start">
                <CheckCircle size={15} className="text-emerald-500 shrink-0 mt-0.5" />
                <span>{learn}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
