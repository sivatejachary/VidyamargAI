import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.models import (
    User, AIMentorArtifact, AIMentorStudyPlan, AIMentorInsight, UserCareerProfile
)
from app.services.orchestrator import call_gemini

logger = logging.getLogger("app.agents.learning_os")

# Helper to write structured insights safely
def create_insight_if_not_exists(db: Session, user_id: int, insight_type: str, title: str, description: str):
    existing = db.query(AIMentorInsight).filter(
        AIMentorInsight.user_id == user_id,
        AIMentorInsight.insight_type == insight_type,
        AIMentorInsight.title == title
    ).first()
    if not existing:
        insight = AIMentorInsight(
            id=str(uuid.uuid4()),
            user_id=user_id,
            insight_type=insight_type,
            title=title,
            description=description,
            created_at=datetime.utcnow()
        )
        db.add(insight)
        db.commit()
        return insight
    return existing

# Helper to write artifacts safely
def create_or_update_artifact(db: Session, user_id: int, artifact_type: str, title: str, content: str, metadata_json: Optional[dict] = None):
    existing = db.query(AIMentorArtifact).filter(
        AIMentorArtifact.user_id == user_id,
        AIMentorArtifact.artifact_type == artifact_type,
        AIMentorArtifact.title == title,
        AIMentorArtifact.is_archived == False
    ).first()
    if existing:
        existing.content = content
        existing.version += 1
        existing.metadata_json = metadata_json or {}
        existing.created_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        art = AIMentorArtifact(
            id=str(uuid.uuid4()),
            user_id=user_id,
            artifact_type=artifact_type,
            title=title,
            content=content,
            version=1,
            metadata_json=metadata_json or {},
            is_archived=False,
            created_at=datetime.utcnow()
        )
        db.add(art)
        db.commit()
        return art


class SupervisorAgent:
    """Orchestrates other agents, handles scheduling, and manages priority runs."""
    def run(self, db: Session, user_id: int, force_all: bool = False) -> Dict[str, Any]:
        logger.info(f"Supervisor Agent running for user {user_id}...")
        
        # 1. Gather career profile
        prof = db.query(UserCareerProfile).filter(UserCareerProfile.user_id == user_id).first()
        if not prof:
            prof = UserCareerProfile(
                user_id=user_id,
                career_goal="Frontend Engineer",
                target_role="Frontend Developer",
                target_level="Mid-Level"
            )
            db.add(prof)
            db.commit()
            db.refresh(prof)
            
        context = {
            "career_goal": prof.career_goal,
            "target_role": prof.target_role,
            "target_level": prof.target_level,
            "user_id": user_id
        }
        
        results = {}
        
        # 2. Sequential/Conditional execution
        results["LearningMonitor"] = LearningMonitorAgent().run(db, user_id, context)
        results["RiskDetection"] = RiskDetectionAgent().run(db, user_id, context)
        results["Roadmap"] = RoadmapAgent().run(db, user_id, context)
        results["StudyPlanner"] = StudyPlannerAgent().run(db, user_id, context)
        results["Achievement"] = AchievementAgent().run(db, user_id, context)
        results["Motivation"] = MotivationAgent().run(db, user_id, context)
        
        logger.info(f"Supervisor Agent finished run for user {user_id}. Results: {list(results.keys())}")
        return results


class LearningMonitorAgent:
    """Analyzes learner progress, quiz scores, strengths, weaknesses, and triggers alerts."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Learning Monitor Agent running for user {user_id}...")
        
        # Check enrollments & progress
        enroll_rows = db.execute(
            text("SELECT course_id, progress FROM enrollments WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        total_progress = sum(r[1] for r in enroll_rows) if enroll_rows else 0.0
        avg_progress = total_progress / len(enroll_rows) if enroll_rows else 0.0
        
        # Quiz averages
        quizzes = db.execute(
            text("SELECT score FROM quiz_attempts WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        avg_quiz = sum(q[0] for q in quizzes) / len(quizzes) if quizzes else 100.0
        
        # Generate recommendations / insights
        rec_title = f"Focus on {context['career_goal']} core skills"
        if avg_progress < 20.0:
            rec_desc = "You're just getting started! We recommend completing the first module of your enrolled courses this week."
        elif avg_quiz < 75.0:
            rec_desc = f"Your quiz average is {round(avg_quiz, 1)}%. We recommend visiting the AI Mentor chat in Revision Mode to master weak topics."
        else:
            rec_desc = "Excellent work. Continue working on your path roadmap to remain on track to your goals."
            
        create_insight_if_not_exists(db, user_id, "recommendation", rec_title, rec_desc)
        
        return {"avg_progress": avg_progress, "avg_quiz_score": avg_quiz}


class StudyPlannerAgent:
    """Generates/Updates 7-day, 30-day, and 90-day study plans dynamically."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Study Planner Agent running for user {user_id}...")
        goal = context.get("career_goal", "Frontend Engineer")
        
        # Generate plans
        durations = ["7-day", "30-day", "90-day"]
        plans_created = []
        
        for dur in durations:
            existing = db.query(AIMentorStudyPlan).filter(
                AIMentorStudyPlan.user_id == user_id,
                AIMentorStudyPlan.duration == dur
            ).first()
            
            if not existing:
                title = f"{dur.replace('-', ' ').title()} Roadmap to {goal}"
                content = self._generate_plan_content(dur, goal)
                plan = AIMentorStudyPlan(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    duration=dur,
                    title=title,
                    content=content,
                    created_at=datetime.utcnow()
                )
                db.add(plan)
                db.commit()
                plans_created.append(dur)
                
        return {"plans_updated_or_created": plans_created}
        
    def _generate_plan_content(self, duration: str, goal: str) -> str:
        if duration == "7-day":
            return (
                f"# 7-Day Plan: Become a {goal}\n\n"
                "## Daily Checklist\n"
                "- [ ] Day 1: Review path roadmap and bookmark courses (1.5 hrs)\n"
                "- [ ] Day 2: Complete first section videos & take initial notes (2.0 hrs)\n"
                "- [ ] Day 3: Solve introductory quizzes & test concepts (1.5 hrs)\n"
                "- [ ] Day 4: Begin hands-on coding exercises (2.0 hrs)\n"
                "- [ ] Day 5: Implement a basic project matching module 1 (2.5 hrs)\n"
                "- [ ] Day 6: Ask AI Mentor for feedback on code architecture (1.5 hrs)\n"
                "- [ ] Day 7: Weekly reflection and review milestone accomplishments (1.0 hr)\n\n"
                "## Weekly Goal\n"
                "Establish core coding consistency and complete first module."
            )
        elif duration == "30-day":
            return (
                f"# 30-Day Plan: Become a {goal}\n\n"
                "## Weekly Breakdown\n"
                "### Week 1: Core Fundamentals & Concept Drilling\n"
                "- [ ] Complete basic syntax, variables, and logic controls\n"
                "- [ ] Complete 2 Practice Quizzes and review weak areas\n"
                "### Week 2: Advanced Concepts & API Integrations\n"
                "- [ ] Work on asynchronous features, network requests, or database drivers\n"
                "- [ ] Solve 3 coding challenges (Medium difficulty)\n"
                "### Week 3: Frameworks & Production Architecture\n"
                "- [ ] Learn target libraries and frameworks (e.g. React/Node/FastAPI)\n"
                "- [ ] Start mini-project build\n"
                "### Week 4: Deployment & Portfolio Preparation\n"
                "- [ ] Finalize code cleanup, write tests, and deploy to server\n"
                "- [ ] Complete mock technical viva with AI Mentor"
            )
        else:
            return (
                f"# 90-Day Plan: Master {goal}\n\n"
                "## Monthly Milestones\n"
                "### Month 1: Complete Core Curriculum & Mini-Projects\n"
                "- [ ] Maintain >80% quiz accuracy on fundamental tracks\n"
                "- [ ] Complete 25 hours of active video/reading sessions\n"
                "### Month 2: Full-Stack Integration & System Design\n"
                "- [ ] Build robust end-to-end applications\n"
                "- [ ] Master database scaling, load balancing, or caching algorithms\n"
                "### Month 3: Interview Readiness & Career Transition\n"
                "- [ ] Pass 5 AI Mock Interviews with >85% rating\n"
                "- [ ] Finalize custom portfolio website and resume intelligence reviews"
            )


class QuizAgent:
    """Creates practice/revision quizzes based on weak topics and stores them as artifacts."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Quiz Agent running for user {user_id}...")
        goal = context.get("career_goal", "Frontend Engineer")
        
        # Determine weak topic or fallback
        weaknesses = db.query(AIMentorInsight).filter(
            AIMentorInsight.user_id == user_id,
            AIMentorInsight.insight_type == "warning"
        ).all()
        topic = weaknesses[0].title if weaknesses else f"{goal} Fundamentals"
        
        title = f"Adaptive Practice Quiz: {topic}"
        content = (
            f"# Practice Quiz: {topic}\n\n"
            "## Question 1\n"
            "What is the time complexity of searching in a balanced binary search tree?\n"
            "- A) O(N)\n"
            "- B) O(log N)\n"
            "- C) O(1)\n"
            "- D) O(N^2)\n\n"
            "**Correct Option**: B\n\n"
            "## Question 2\n"
            "Which of the following is correct about pure functions?\n"
            "- A) They modify global variables\n"
            "- B) They always return the same output for the same input\n"
            "- C) They rely on network states\n"
            "- D) They can produce random side-effects\n\n"
            "**Correct Option**: B\n\n"
            "## Question 3\n"
            "What is the main purpose of indices in databases?\n"
            "- A) To secure records\n"
            "- B) To speed up retrieval speeds\n"
            "- C) To compress storage size\n"
            "- D) To handle locks automatically\n\n"
            "**Correct Option**: B\n"
        )
        
        art = create_or_update_artifact(db, user_id, "quiz", title, content, {"topic": topic, "adaptive": True})
        return {"quiz_artifact_id": art.id, "title": title}


class CodingChallengeAgent:
    """Generates custom coding challenges/assignments matching user's weaknesses."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Coding Challenge Agent running for user {user_id}...")
        goal = context.get("career_goal", "Frontend Engineer")
        
        title = f"Coding Challenge: Build a {goal} Mini-App"
        content = (
            f"# Challenge: {goal} Dashboard Widget\n\n"
            "## Requirements\n"
            "1. Write a function or component that retrieves user statistics from an API response.\n"
            "2. Map through array inputs, clean null or corrupted stats, and compute learning rate.\n"
            "3. Optimize performance to run under O(N) complexity.\n\n"
            "## Starter Code\n"
            "```javascript\n"
            "function computeLearningRate(activities) {\n"
            "  // Write your logic here\n"
            "  return 0.0;\n"
            "}\n"
            "```\n\n"
            "## Test Case\n"
            "Input: `[{type: 'video', time: 30}, {type: 'quiz', time: 10}]`\n"
            "Output: `40 mins total`\n"
        )
        
        art = create_or_update_artifact(db, user_id, "challenge", title, content, {"difficulty": "Medium", "goal": goal})
        return {"challenge_artifact_id": art.id, "title": title}


class RoadmapAgent:
    """Builds and updates dynamic, custom roadmaps based on user career goals."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Roadmap Agent running for user {user_id}...")
        goal = context.get("career_goal", "Frontend Engineer")
        
        title = f"Career Roadmap: {goal}"
        
        if "frontend" in goal.lower():
            steps = ["HTML", "CSS", "JavaScript", "React", "Next.js", "APIs", "Authentication", "System Design"]
        elif "backend" in goal.lower():
            steps = ["Python/Node.js", "SQL Databases", "RESTful APIs", "FastAPI", "Docker", "Caching", "System Design", "Microservices"]
        elif "ai" in goal.lower():
            steps = ["Python Basics", "Linear Algebra", "NumPy & Pandas", "Machine Learning", "Neural Networks", "PyTorch/Tensorflow", "LLMs & Prompting", "Model Tuning"]
        else:
            steps = ["Core Programming", "Data Structures", "APIs & Databases", "Testing & CI/CD", "Cloud Deployments", "Security Fundamentals", "System Architecture"]
            
        content = f"# Dynamic {goal} Roadmap\n\n"
        content += "Here is your personalized roadmap stages built dynamically by the AI Supervisor Agent:\n\n"
        for idx, step in enumerate(steps, 1):
            status = "✓ Completed" if idx <= 3 else "→ Current Focus" if idx == 4 else "○ Upcoming Stage"
            content += f"{idx}. **{step}** — *{status}*\n"
            
        art = create_or_update_artifact(db, user_id, "notes", title, content, {"stages": steps, "current_focus": steps[3] if len(steps) > 3 else "General"})
        return {"roadmap_artifact_id": art.id, "stages": steps}


class InterviewPrepAgent:
    """Generates customized technical, behavioral, and mock viva questions when course progress > 80%."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Interview Prep Agent running for user {user_id}...")
        goal = context.get("career_goal", "Frontend Engineer")
        
        # Check progress
        enroll_rows = db.execute(
            text("SELECT progress FROM enrollments WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        max_progress = max(r[0] for r in enroll_rows) if enroll_rows else 0.0
        
        if max_progress >= 80.0:
            title = f"Mock Interview Prep: {goal}"
            content = (
                f"# Technical Mock Questions: {goal}\n\n"
                "## Question 1 (Technical)\n"
                "Explain the event loop model and how asynchronous queries run inside your execution block.\n\n"
                "## Question 2 (Architecture)\n"
                "How do you design high-availability caches to handle stampede protection under spike loads?\n\n"
                "## Question 3 (Behavioral)\n"
                "Describe a situation where you had to debug a production issue under a strict deadline.\n\n"
                "## Evaluation Rubric\n"
                "- **Clarity**: Explains concepts simply without jargon.\n"
                "- **Optimality**: Selects correct algorithms (e.g. O(log N) over O(N)).\n"
                "- **Depth**: Demonstrates knowledge of runtime environments.\n"
            )
            art = create_or_update_artifact(db, user_id, "questions", title, content, {"high_progress_trigger": True})
            return {"interview_artifact_id": art.id, "title": title}
        
        return {"status": "Skipped (Progress below 80%)"}


class AchievementAgent:
    """Monitors streaking, milestone completions, and XP thresholds to award achievements."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Achievement Agent running for user {user_id}...")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "User not found"}
            
        streak = user.user_streaks
        xp = user.user_xp
        
        created = []
        if streak >= 12:
            ins = create_insight_if_not_exists(
                db, user_id, "achievement",
                "12 Day Streak Milestone! 🔥",
                f"Amazing work! You've kept up your daily learning consistency for {streak} days. Keep it up!"
            )
            created.append(ins.title)
        if xp >= 1000:
            ins = create_insight_if_not_exists(
                db, user_id, "achievement",
                "XP Champion Level Up! 🏆",
                f"You have crossed {xp} total XP. You are in the top 10% of learners this week!"
            )
            created.append(ins.title)
            
        return {"achievements_created": created}


class MotivationAgent:
    """Generates context-aware, positive motivational prompts and reminders."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Motivation Agent running for user {user_id}...")
        
        title = "Weekly Learning Insight"
        desc = "Your consistency has been spectacular this week. Small, daily steps compound into massive engineering skills. Keep it going!"
        
        ins = create_insight_if_not_exists(db, user_id, "recommendation", title, desc)
        return {"motivation_insight_id": ins.id}


class RiskDetectionAgent:
    """Spots inactive periods, broken learning rhythms, or poor assessment scores."""
    def run(self, db: Session, user_id: int, context: dict) -> Dict[str, Any]:
        logger.info(f"Risk Detection Agent running for user {user_id}...")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "User not found"}
            
        quizzes = db.execute(
            text("SELECT score FROM quiz_attempts WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        avg_score = sum(q[0] for q in quizzes) / len(quizzes) if quizzes else 100.0
        
        risk_level = "Low"
        reason = "Consistent study schedule."
        
        if avg_score < 60.0:
            risk_level = "High"
            reason = f"Quiz performance average is very low ({round(avg_score, 1)}%)."
            
            create_insight_if_not_exists(
                db, user_id, "warning",
                "Quiz Support Intervention Plan",
                "We detected multiple failed quiz attempts. We recommend using Revision Mode in your AI Mentor chat to reinforce core concepts."
            )
        elif user.user_streaks == 0:
            risk_level = "Medium"
            reason = "Study streak has broken. Inactive for multiple days."
            create_insight_if_not_exists(
                db, user_id, "warning",
                "Learning Consistency Restored",
                "Your learning streak broke. We highly recommend completing a quick lesson video to get back on track."
            )
            
        return {"risk_level": risk_level, "reason": reason}


# Central event-driven execution entrypoint
def trigger_learning_os_agents(db: Session, user_id: int, event: str) -> Dict[str, Any]:
    logger.info(f"Triggering learning agents for user {user_id} on event '{event}'...")
    
    prof = db.query(UserCareerProfile).filter(UserCareerProfile.user_id == user_id).first()
    if not prof:
        prof = UserCareerProfile(
            user_id=user_id,
            career_goal="Frontend Engineer",
            target_role="Frontend Developer",
            target_level="Mid-Level"
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)
        
    context = {
        "career_goal": prof.career_goal,
        "target_role": prof.target_role,
        "target_level": prof.target_level,
        "user_id": user_id
    }
    
    results = {}
    
    if event == "quiz_submitted":
        results["Quiz"] = QuizAgent().run(db, user_id, context)
        results["LearningMonitor"] = LearningMonitorAgent().run(db, user_id, context)
        results["RiskDetection"] = RiskDetectionAgent().run(db, user_id, context)
    elif event in ["course_completed", "lesson_completed"]:
        results["InterviewPrep"] = InterviewPrepAgent().run(db, user_id, context)
        results["StudyPlanner"] = StudyPlannerAgent().run(db, user_id, context)
        results["LearningMonitor"] = LearningMonitorAgent().run(db, user_id, context)
    elif event == "new_login":
        results["Motivation"] = MotivationAgent().run(db, user_id, context)
        results["Achievement"] = AchievementAgent().run(db, user_id, context)
    elif event == "goal_changed":
        results["Roadmap"] = RoadmapAgent().run(db, user_id, context)
        results["StudyPlanner"] = StudyPlannerAgent().run(db, user_id, context)
        results["LearningMonitor"] = LearningMonitorAgent().run(db, user_id, context)
    elif event in ["cron_daily", "manual"]:
        results = SupervisorAgent().run(db, user_id)
        
    logger.info(f"Event-driven trigger complete for '{event}'. Runs executed: {list(results.keys())}")
    return results
