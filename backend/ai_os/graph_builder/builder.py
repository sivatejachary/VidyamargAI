import logging
from typing import List, Dict, Any
from collections import deque

logger = logging.getLogger("ai_os.graph_builder.builder")

class GraphBuilder:
    """
    Validates goal nodes dependencies and computes execution orders.
    """
    def __init__(self):
        pass

    def build_execution_order(self, subgoals: List[Dict[str, Any]]) -> List[str]:
        """
        Runs a topological sort (Kahn's algorithm) to detect cycles and sort execution nodes.
        """
        logger.info("Building topological execution order for goal DAG...")
        
        # Build adjacency lists and calculate in-degrees
        adj_list: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}
        
        for sg in subgoals:
            sg_id = sg["id"]
            adj_list[sg_id] = []
            in_degree[sg_id] = 0

        for sg in subgoals:
            sg_id = sg["id"]
            deps = sg.get("dependencies", [])
            for dep in deps:
                if dep not in adj_list:
                    # Ignore invalid dependencies to prevent crashes
                    continue
                # Prerequisite dep points to sg_id
                adj_list[dep].append(sg_id)
                in_degree[sg_id] += 1

        # Kahn's algorithm queue
        queue = deque([node for node in in_degree if in_degree[node] == 0])
        topological_order = []

        while queue:
            node = queue.popleft()
            topological_order.append(node)
            
            for neighbor in adj_list.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Cycle detection
        if len(topological_order) != len(subgoals):
            logger.critical("Dependency loop detected! Goal tree is not a Directed Acyclic Graph (DAG).")
            raise ValueError("Dependency cycle detected inside Goal Tree.")
            
        logger.info(f"Topological order computed: {topological_order}")
        return topological_order
