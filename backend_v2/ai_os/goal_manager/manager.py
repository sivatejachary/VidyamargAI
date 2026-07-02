import logging
from typing import Dict, Any, List
from ..schemas.goal import GoalTree, SubGoal, GoalStatus

logger = logging.getLogger("ai_os.goal_manager.manager")

class GoalManager:
    """
    Manages candidate career goal trees and calculates progress milestones.
    """
    def __init__(self, db_session: Any):
        self.db = db_session

    async def initialize_goal_tree(self, tree_id: str, candidate_id: str, career_role: str, subgoals_def: List[Dict[str, Any]]) -> GoalTree:
        """
        Builds a new Goal Tree with subgoal nodes.
        """
        logger.info(f"Initializing goal tree '{tree_id}' for candidate '{candidate_id}' targeting '{career_role}'")
        
        subgoals = {}
        for sg in subgoals_def:
            sg_id = sg["id"]
            subgoals[sg_id] = SubGoal(
                id=sg_id,
                name=sg["name"],
                description=sg["description"],
                weight=sg.get("weight", 1.0),
                dependencies=sg.get("dependencies", []),
                status=GoalStatus.PENDING,
                progress=0.0
            )

        tree = GoalTree(
            id=tree_id,
            candidate_id=candidate_id,
            target_career=career_role,
            status=GoalStatus.PENDING,
            overall_progress=0.0,
            subgoals=subgoals
        )
        
        # Save tree configuration to DB
        return tree

    async def update_subgoal_progress(self, tree: GoalTree, subgoal_id: str, progress: float, status: GoalStatus) -> GoalTree:
        """
        Updates a subgoal progress and recalculates overall goal tree completion index.
        """
        if subgoal_id not in tree.subgoals:
            logger.warning(f"Subgoal '{subgoal_id}' not found in goal tree '{tree.id}'")
            return tree

        sg = tree.subgoals[subgoal_id]
        sg.progress = max(0.0, min(100.0, progress))
        sg.status = status
        
        logger.info(f"Subgoal '{subgoal_id}' updated: Progress={sg.progress}%, Status={sg.status}")
        
        # Recalculate overall progress using weighted math index
        # Overall Progress = Sum(weight * progress) / Sum(weight)
        total_weight = 0.0
        weighted_sum = 0.0
        
        all_completed = True
        for node_id, node in tree.subgoals.items():
            total_weight += node.weight
            weighted_sum += node.weight * (node.progress / 100.0)
            if node.status != GoalStatus.COMPLETED:
                all_completed = False

        if total_weight > 0:
            tree.overall_progress = (weighted_sum / total_weight) * 100.0
            
        if all_completed:
            tree.status = GoalStatus.COMPLETED
        elif any(node.status == GoalStatus.IN_PROGRESS for node in tree.subgoals.values()):
            tree.status = GoalStatus.IN_PROGRESS

        logger.info(f"Goal Tree '{tree.id}' recalculated. Overall Progress: {tree.overall_progress:.2f}%")
        return tree
