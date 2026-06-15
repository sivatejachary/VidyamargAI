import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RankingAgent:
    def __init__(self, matched_jobs: List[Dict[str, Any]]):
        self.matched_jobs = matched_jobs

    def rank_jobs(self, log_fn=None) -> List[Dict[str, Any]]:
        """
        Ranks jobs based on:
        - Resume Match Score: 70% weight
        - Verification Score (Job Consistency): 20% weight
        - Freshness: 10% weight
        
        Final Ranking Score = (Match Score * 0.70) + (Verification Score * 0.20) + (Freshness * 0.10)
        """
        if log_fn:
            log_fn("Ranking opportunities based on Match Score, Verification Score, and Freshness...", "info")

        ranked_list = []
        for item in self.matched_jobs:
            # 1. Match score (already calculated out of 100)
            match_score = item["match_score"]

            # 2. Verification score (20%)
            verification_score = item.get("verification_score", 100) # default to 100 if not present

            # 3. Freshness score (10%)
            posted = str(item.get("posted_date", "")).lower()
            if "today" in posted or "1 day" in posted or "recently" in posted or "recent" in posted:
                freshness_score = 100.0
            elif "2 days" in posted or "3 days" in posted:
                freshness_score = 80.0
            elif "week" in posted:
                freshness_score = 60.0
            else:
                freshness_score = 40.0

            # Calculate Final Ranking Score
            ranking_score = (
                (match_score * 0.70) +
                (verification_score * 0.20) +
                (freshness_score * 0.10)
            )
            ranking_score = min(100, int(round(ranking_score)))

            # Save in item
            item["ranking_score"] = ranking_score
            ranked_list.append(item)

        # Sort descending by ranking score
        ranked_list.sort(key=lambda x: x["ranking_score"], reverse=True)

        if log_fn:
            log_fn("Opportunities successfully ranked", "success")

        logger.info(f"RankingAgent: Ranked {len(ranked_list)} jobs")
        return ranked_list
