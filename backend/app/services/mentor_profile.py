import json
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.models import User, CourseProgress, LearningEvent, AIMentorInsight

logger = logging.getLogger("app.mentor_profile")

def get_learning_health(db: Session, user_id: int) -> tuple[float, str]:
    """
    Calculates weighted learning health score (0-100):
    - 40% Course Progress: Average completion of all enrolled courses
    - 25% Quiz Performance: Average score of all quiz attempts (defaults to 100 if none)
    - 15% Assessment Completion: Percentage of completed written assessments & AI interviews
    - 10% Streak: Proportional streak score (min(streak * 4, 100))
    - 10% Weekly Activity: Past 7 days events count (min(event_count * 10, 100))
    """
    try:
        # 1. Course Progress (40%)
        courses_res = db.execute(
            text("SELECT progress FROM enrollments WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        if courses_res:
            avg_progress = sum(r[0] for r in courses_res) / len(courses_res)
        else:
            avg_progress = 0.0
            
        # 2. Quiz Performance (25%)
        quizzes_res = db.execute(
            text("SELECT score FROM quiz_attempts WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        if quizzes_res:
            avg_quiz = sum(r[0] for r in quizzes_res) / len(quizzes_res)
        else:
            avg_quiz = 100.0  # Default to full score if no quizzes attempted
            
        # 3. Assessment Completion (15%)
        prog_res = db.execute(
            text('SELECT "writtenCompleted", "interviewCompleted" FROM user_progress WHERE "userId" = :user_id'),
            {"user_id": user_id}
        ).fetchall()
        
        if prog_res:
            completed_assessments = sum((1 if r[0] else 0) + (1 if r[1] else 0) for r in prog_res)
            total_possible = len(prog_res) * 2
            assessment_completion = (completed_assessments / total_possible) * 100.0 if total_possible > 0 else 100.0
        else:
            assessment_completion = 100.0
            
        # 4. Streak (10%)
        user_row = db.execute(
            text("SELECT user_streaks FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        streak = user_row[0] if user_row else 0
        streak_score = min(streak * 4, 100.0)
        
        # 5. Weekly Activity (10%)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        activity_res = db.execute(
            text("SELECT COUNT(id) FROM learning_events WHERE user_id = :user_id AND created_at >= :seven_days_ago"),
            {"user_id": user_id, "seven_days_ago": seven_days_ago}
        ).fetchone()
        events_count = activity_res[0] if activity_res else 0
        activity_score = min(events_count * 10, 100.0)
        
        # Calculate final weighted score
        final_score = (
            (avg_progress * 0.40) +
            (avg_quiz * 0.25) +
            (assessment_completion * 0.15) +
            (streak_score * 0.10) +
            (activity_score * 0.10)
        )
        
        final_score = round(max(0.0, min(100.0, final_score)), 2)
        
        # Determine Status Bracket
        if final_score < 40:
            status = "At Risk"
        elif final_score < 70:
            status = "Improving"
        elif final_score < 90:
            status = "Good Progress"
        else:
            status = "Excellent"
            
        return final_score, status
    except Exception as e:
        logger.error(f"Error calculating learning health: {e}")
        return 75.0, "Good Progress"

def get_risk_analysis(db: Session, user_id: int) -> tuple[str, str]:
    """
    Performs rule-based Learning Risk Detection:
    - High Risk:
      - No activity for 7+ days, OR
      - Average quiz score < 50%, OR
      - Multiple failed assessments (e.g. 2+ attempts with score < 60% in past 14 days)
    - Medium Risk:
      - Inactivity for 3-6 days, OR
      - Average quiz score 50%-65%, OR
      - Course progress stalled for 5+ days
    - Low Risk: Default safe state
    """
    try:
        # Check last active date
        user_row = db.execute(
            text("SELECT last_active_date FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        last_active = user_row[0] if user_row and user_row[0] else None
        days_inactive = (datetime.utcnow() - last_active).days if last_active else 10 # Default to 10 if not logged
        
        # Check average quiz score
        quiz_scores = db.execute(
            text("SELECT score FROM quiz_attempts WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        avg_quiz = sum(r[0] for r in quiz_scores) / len(quiz_scores) if quiz_scores else 100.0
        
        # Check failed quizzes in past 14 days
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        failed_quizzes = db.execute(
            text("SELECT COUNT(id) FROM quiz_attempts WHERE user_id = :user_id AND score < 60 AND created_at >= :two_weeks_ago"),
            {"user_id": user_id, "two_weeks_ago": two_weeks_ago}
        ).fetchone()[0]
        
        # Check if progress is stalled
        progress_res = db.execute(
            text('SELECT "overall_progress", "last_activity" FROM course_progress WHERE "user_id" = :user_id'),
            {"user_id": user_id}
        ).fetchall()
        
        stalled = False
        stalled_days = 0
        if progress_res:
            for p in progress_res:
                if p[0] < 100.0 and p[1]:
                    inactive_days = (datetime.utcnow() - p[1]).days
                    if inactive_days >= 5:
                        stalled = True
                        stalled_days = max(stalled_days, inactive_days)
                        
        # High Risk Classification
        if days_inactive >= 7:
            return "High", f"No login or platform activity detected for {days_inactive} days. Let's resume learning!"
        if avg_quiz < 50.0:
            return "High", f"Average quiz score ({round(avg_quiz)}%) is below passing threshold. Review of core concepts recommended."
        if failed_quizzes >= 2:
            return "High", "Multiple failed quiz attempts in the last 14 days. Suggest starting a revision session."
            
        # Medium Risk Classification
        if days_inactive >= 3:
            return "Medium", f"No active study sessions for {days_inactive} days. Recommended action: complete your next topic."
        if avg_quiz < 65.0:
            return "Medium", f"Average quiz score ({round(avg_quiz)}%) indicates difficulty with some topics. Try taking practice quizzes."
        if stalled:
            return "Medium", f"Course completion progress has been stalled for {stalled_days} days. Review study guides to unlock the next module."
            
        return "Low", "Learning metrics are steady. Keep up the consistent effort!"
    except Exception as e:
        logger.error(f"Error calculating risk analysis: {e}")
        return "Low", "Steady learning activity."

def get_smart_recommendations(db: Session, user_id: int) -> tuple[list[str], str, list[str], list[str]]:
    """
    Returns prioritized recommendations, estimated time, strengths, and weaknesses:
    Priority 1: Incomplete lessons/PDFs of enrolled courses
    Priority 2: Failed/incomplete quizzes
    Priority 3: Pending module written/interview assessments
    Priority 4: Un-enrolled courses
    """
    strengths = []
    weaknesses = []
    recommendations = []
    upcoming_assessments = []
    estimated_minutes = 0
    
    try:
        # Load enrolled courses
        enrollments = db.execute(
            text("SELECT course_id FROM enrollments WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        enrolled_ids = [e[0] for e in enrollments]
        
        # 1. Compile strengths & weaknesses based on quizzes & module progress
        for cid in enrolled_ids:
            course_title = db.execute(text("SELECT title FROM courses WHERE id = :cid"), {"cid": cid}).fetchone()
            c_title = course_title[0] if course_title else cid
            
            modules = db.execute(
                text('SELECT id, title FROM modules WHERE courseId = :cid'),
                {"cid": cid}
            ).fetchall()
            
            for m in modules:
                m_id, m_title = m
                prog = db.execute(
                    text('SELECT "videoCompleted", "pdfCompleted", "quizCompleted", "writtenCompleted", "interviewCompleted" FROM user_progress WHERE "userId" = :user_id AND "moduleId" = :m_id'),
                    {"user_id": user_id, "m_id": m_id}
                ).fetchone()
                
                # Fetch quiz attempts for this module's quiz
                quiz = db.execute(text('SELECT id FROM quizzes WHERE "moduleId" = :m_id'), {"m_id": m_id}).fetchone()
                quiz_score = None
                if quiz:
                    quiz_attempt = db.execute(
                        text("SELECT score FROM quiz_attempts WHERE user_id = :user_id AND quiz_id = :qid ORDER BY score DESC"),
                        {"user_id": user_id, "qid": quiz[0]}
                    ).fetchone()
                    if quiz_attempt:
                        quiz_score = quiz_attempt[0]
                        
                # Categorize strengths/weaknesses
                if prog:
                    if quiz_score is not None:
                        if quiz_score >= 70.0:
                            strengths.append(f"{c_title}: {m_title} (Quiz: {round(quiz_score)}%)")
                        elif quiz_score < 60.0:
                            weaknesses.append(f"{c_title}: {m_title} (Functions/Topics)")
                    elif prog[0] and prog[1]:  # completed video + pdf but no quiz
                        weaknesses.append(f"{c_title}: {m_title} (Quiz pending)")
                
                # Generate Recommendations based on priorities
                # Priority 1: Incomplete lessons
                topics = db.execute(
                    text("SELECT id, title, estimatedduration FROM topics WHERE moduleid = :m_id ORDER BY topicno"),
                    {"m_id": m_id}
                ).fetchall()
                
                for t in topics:
                    t_id, t_title, t_dur = t
                    lesson = db.execute(text("SELECT id FROM lessons WHERE topicid = :t_id"), {"t_id": t_id}).fetchone()
                    pdf = db.execute(text("SELECT id FROM pdfs WHERE topicid = :t_id"), {"t_id": t_id}).fetchone()
                    
                    video_done = prog[0] if prog else False
                    pdf_done = prog[1] if prog else False
                    
                    if lesson and not video_done:
                        rec = f"Watch video lesson: '{t_title}' in {m_title}"
                        if rec not in recommendations:
                            recommendations.append(rec)
                            estimated_minutes += 20
                    if pdf and not pdf_done:
                        rec = f"Review reading workbook: '{t_title}'"
                        if rec not in recommendations:
                            recommendations.append(rec)
                            estimated_minutes += 15
                            
                # Priority 2: Failed/incomplete quizzes
                if quiz:
                    quiz_done = prog[2] if prog else False
                    if not quiz_done or (quiz_score is not None and quiz_score < 60.0):
                        action = f"Take '{m_title}' Practice Quiz" if not quiz_done else f"Retake failed '{m_title}' quiz (Score: {round(quiz_score)}%)"
                        if action not in recommendations:
                            recommendations.append(action)
                            estimated_minutes += 15
                            
                # Priority 3: Written assessments & AI interviews
                written = db.execute(text("SELECT id, title FROM written_assessments WHERE moduleid = :m_id"), {"m_id": m_id}).fetchone()
                if written and not (prog[3] if prog else False):
                    action = f"Complete Assessment: '{written[1]}'"
                    upcoming_assessments.append(action)
                    if action not in recommendations:
                        recommendations.append(action)
                        estimated_minutes += 30
                        
                ai_interview = db.execute(text("SELECT id, title FROM ai_interviews WHERE moduleid = :m_id"), {"m_id": m_id}).fetchone()
                if ai_interview and not (prog[4] if prog else False):
                    action = f"Complete AI Interview: '{ai_interview[1]}'"
                    upcoming_assessments.append(action)
                    if action not in recommendations:
                        recommendations.append(action)
                        estimated_minutes += 30

        # Priority 4: Non-enrolled courses if recommendation list is small
        if len(recommendations) < 3:
            all_courses = db.execute(text("SELECT id, title FROM courses WHERE status = 'active'")).fetchall()
            for c in all_courses:
                if c[0] not in enrolled_ids:
                    action = f"Enroll in Course: '{c[1]}' to expand your skills"
                    if action not in recommendations:
                        recommendations.append(action)
                        estimated_minutes += 60
                        if len(recommendations) >= 5:
                            break

        # Defaults if clean slate
        if not strengths:
            strengths = ["Learning Streak Setup", "Getting Started"]
        if not weaknesses:
            weaknesses = ["No critical weaknesses identified yet! Keep learning."]
        if not recommendations:
            recommendations = ["Explore the catalog and enroll in a new Skill Lab course!"]
            estimated_minutes = 60
            
        # Format estimated time
        hours = estimated_minutes // 60
        mins = estimated_minutes % 60
        if hours > 0:
            est_time = f"{hours}h {mins}m" if mins > 0 else f"{hours} hours"
        else:
            est_time = f"{mins} minutes"
            
        return recommendations[:3], est_time, strengths[:3], weaknesses[:3]
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return ["Resume python lessons"], "1.5 hours", ["Python Intro"], ["None"]

def trigger_background_insights(db: Session, user_id: int):
    """
    Scans candidate database logs on learning triggers (e.g. quiz submit, lesson complete)
    and dynamically inserts Achievements, Warnings, and Recommendation cards.
    """
    try:
        # 1. Check Course completions
        courses_res = db.execute(
            text("SELECT course_id, progress FROM enrollments WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        for row in courses_res:
            cid, progress = row
            if progress >= 100.0:
                course_title = db.execute(text("SELECT title FROM courses WHERE id = :cid"), {"cid": cid}).fetchone()
                title = course_title[0] if course_title else cid
                
                # Check if achievement already exists
                existing = db.query(AIMentorInsight).filter(
                    AIMentorInsight.user_id == user_id,
                    AIMentorInsight.insight_type == "achievement",
                    AIMentorInsight.title == f"Completed {title}"
                ).first()
                
                if not existing:
                    insight = AIMentorInsight(
                        user_id=user_id,
                        insight_type="achievement",
                        title=f"Completed {title}",
                        description=f"Congratulations! You've successfully finished all modules and validated this course."
                    )
                    db.add(insight)
                    logger.info(f"Added achievement insight for user {user_id}")
                    
        # 2. Check failed quizzes (Warning)
        failed_res = db.execute(
            text("SELECT qa.quiz_id, qa.score, q.title FROM quiz_attempts qa JOIN quizzes q ON qa.quiz_id = q.id WHERE qa.user_id = :user_id AND qa.score < 60.0 ORDER BY qa.created_at DESC LIMIT 1"),
            {"user_id": user_id}
        ).fetchone()
        
        if failed_res:
            qid, score, q_title = failed_res
            title_text = f"Quiz Score Drop: {q_title}"
            
            existing = db.query(AIMentorInsight).filter(
                AIMentorInsight.user_id == user_id,
                AIMentorInsight.insight_type == "warning",
                AIMentorInsight.title == title_text
            ).first()
            
            if not existing:
                insight = AIMentorInsight(
                    user_id=user_id,
                    insight_type="warning",
                    title=title_text,
                    description=f"You scored {round(score)}% in the '{q_title}' quiz, which is below the 60% passing threshold. Try reviewing the topics before retaking."
                )
                db.add(insight)
                logger.info(f"Added warning insight for user {user_id}")
                
        # 3. Check for progress stalls (Recommendation)
        stalled_res = db.execute(
            text('SELECT cp.course_id, cp.overall_progress, c.title, cp.last_activity FROM course_progress cp JOIN courses c ON cp.course_id = c.id WHERE cp.user_id = :user_id AND cp.overall_progress < 100.0'),
            {"user_id": user_id}
        ).fetchall()
        
        for row in stalled_res:
            cid, progress, c_title, last_act = row
            if last_act:
                inactive_days = (datetime.utcnow() - last_act).days
                if inactive_days >= 5:
                    title_text = f"Stalled Course: {c_title}"
                    existing = db.query(AIMentorInsight).filter(
                        AIMentorInsight.user_id == user_id,
                        AIMentorInsight.insight_type == "recommendation",
                        AIMentorInsight.title == title_text
                    ).first()
                    
                    if not existing:
                        insight = AIMentorInsight(
                            user_id=user_id,
                            insight_type="recommendation",
                            title=title_text,
                            description=f"You haven't updated your progress in '{c_title}' for {inactive_days} days. We recommend completing 2 lessons to restart your momentum."
                        )
                        db.add(insight)
                        logger.info(f"Added recommendation insight for user {user_id}")
                        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing background insights: {e}")
