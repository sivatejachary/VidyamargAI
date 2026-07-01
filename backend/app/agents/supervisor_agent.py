import json
import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.agents.base import JobAgentState
from app.agents.blackboard import Blackboard, Evidence, GoalNode
from app.tools.registry import tool_registry
from app.services.policy_engine import PolicyEngine
from app.services.goal_manager import GoalManager
from app.services.event_bus import event_bus
from app.services.orchestrator import call_nvidia, call_gemini
from app.models.mcp_models import AgentExecutionHistory
from app.models.models import Candidate
from app.models.models import User

logger = logging.getLogger("app.agents.supervisor_agent")

class SupervisorAgent:
    async def think(self, state: JobAgentState, db: Session) -> Dict[str, Any]:
        """
        Think node: Analyze blackboard state, memory, goal graph, and query LLM for next action.
        """
        cand = db.query(Candidate).filter(Candidate.user_id == state.user_id).first()
        preferences_summary = cand.skills or "No skills recorded yet."
        
        # Compile tools schema with priority/cost/reliability metadata
        tool_schemas = json.dumps(tool_registry.get_schemas(), indent=2)
        
        # Format history
        history_summary = ""
        for i, step in enumerate(state.execution_steps):
            history_summary += f"Step {i+1}:\n"
            history_summary += f"Progress: {step.get('progress_updates')}\n"
            history_summary += f"Actions: {step.get('actions')}\n"
            history_summary += f"Responses: {step.get('responses')}\n\n"
            
        # Serialize current Blackboard state
        bb = state.blackboard
        blackboard_summary = json.dumps(bb.model_dump(mode="json"), indent=2) if bb else "No blackboard initialized."
            
        system_prompt = f"""
You are an autonomous job search agent acting on behalf of a candidate.
Your goal is to achieve the user's objective using the tools and capabilities available.
You operate in a Think -> Act -> Observe -> Reflect loop.

Candidate Profile Summary:
{preferences_summary}

Goal Stack:
- Main Goal: {state.main_goal}
- Subgoal: {state.subgoal or "None"}
- Current Task: {state.current_task or "None"}

Execution History so far:
{history_summary or "No steps executed yet."}

Current Shared Execution Blackboard:
{blackboard_summary}

Available capabilities and tools schemas:
{tool_schemas}

INSTRUCTIONS:
1. Do NOT include user-facing reasoning thoughts in your response. Keep them strictly in the "thought" trace field of the JSON.
2. Provide a list of concise progress logs for the user interface under "progress_updates" (e.g. `["Broadening search scope...", "Filtering remote jobs..."]`).
3. Update the "blackboard" object:
   - Modify "known_facts", "unknown_facts", "assumptions", "completed_tasks", "pending_tasks".
   - Modify the "goal_graph" (add/update tasks with status, dependencies, priority, retry_budget).
   - If the strategy, graph structures, or priorities mutate, increment "plan_version" and append the reason to "plan_history".
4. Under "next_actions", output a list of actions to execute. Each action is either a concrete tool name OR a capability name (e.g. "job_search"), plus its required arguments.
5. If independent tasks can run concurrently to reduce latency, output multiple actions under "next_actions". Otherwise output exactly one.
6. Set your "confidence" score between 0.0 and 1.0. If confidence < 0.75 or if you require user choices/files/approvals, provide "clarification_question" AND describe the interactive component under "interactive_card" (e.g. type: "single_select", "slider", "upload", "approval", "schedule" etc. with fields, options, and required flag).
7. If the main goal has been successfully completed, set action to "finish".

You must return ONLY a valid JSON object matching this structure:
{{
  "thought": "Internal trace explaining next step rationale (hidden from user)",
  "progress_updates": ["Concise progress log 1", "Concise progress log 2"],
  "goal_stack": {{
    "main_goal": "...",
    "subgoal": "...",
    "current_task": "..."
  }},
  "blackboard": {{
    "known_facts": [...],
    "unknown_facts": [...],
    "assumptions": [...],
    "blocked_items": [...],
    "completed_tasks": [...],
    "pending_tasks": [...],
    "evidence_graph": {{
      "fact_id_or_ref": {{
         "fact_id": "...",
         "source_type": "...",
         "source_ref": "...",
         "confidence_score": 1.0,
         "verified_by": [...]
      }}
    }},
    "goal_graph": {{
      "node_id": {{
         "node_id": "...",
         "label": "...",
         "status": "pending",
         "priority": 50,
         "dependencies": [],
         "retry_budget": 2,
         "confidence_score": 1.0
      }}
    }},
    "plan_version": 1,
    "plan_history": []
  }},
  "next_actions": [
    {{
      "tool_or_capability": "postgres_job_search",
      "args": {{ ... }}
    }}
  ],
  "confidence": 0.95,
  "clarification_question": null,
  "interactive_card": null
}}
"""
        response_text = ""
        try:
            messages = [{"role": "user", "content": system_prompt}]
            response_text = call_nvidia(messages)
            if not response_text:
                response_text = call_gemini(system_prompt, json_mode=True)
        except Exception as e:
            logger.error(f"LLM call failed in think node: {e}")
            
        parsed_data = {}
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            parsed_data = json.loads(clean_text.strip())
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {response_text}. Error: {e}")
            
        return parsed_data

    async def execute_actions_with_escalation(self, state: JobAgentState, actions: List[Dict[str, Any]], db: Session) -> Dict[str, Any]:
        """
        Executes actions with capability resolution, policy checks, timeouts, and Dynamic Escalation Recovery.
        """
        resolved_tools = []
        
        # 1. Capability Resolution & Policy Checking
        for act in actions:
            target = act.get("tool_or_capability")
            args = act.get("args", {})
            
            tool = tool_registry.resolve_capability(target)
            if not tool:
                msg = f"Capability or tool '{target}' could not be resolved."
                resolved_tools.append({
                    "tool": None,
                    "target": target,
                    "args": args,
                    "error": {"status": "error", "message": msg, "failure_classification": "PERMANENT"}
                })
                continue
                
            allowed, msg = PolicyEngine.evaluate(state.user_id, state.user_role, tool, args)
            if not allowed:
                await event_bus.publish("policy_violation", {
                    "user_id": state.user_id,
                    "tool_name": tool.name,
                    "reason": msg
                })
                resolved_tools.append({
                    "tool": tool,
                    "target": target,
                    "args": args,
                    "error": {"status": "error", "message": f"Policy Blocked: {msg}", "failure_classification": "PERMANENT"}
                })
            else:
                resolved_tools.append({
                    "tool": tool,
                    "target": target,
                    "args": args,
                    "error": None
                })
                
        # 2. Execute resolved tools with Escalation Tree fallback
        loop_start = time.time()
        
        async def _execute_single_action(item) -> Dict[str, Any]:
            tool = item["tool"]
            args = item["args"]
            target = item["target"]
            err = item["error"]
            
            if err:
                return err
                
            from app.services.tool_memory import tool_memory
            
            # Escalation escalation loop
            retry_count = 0
            max_retries = getattr(tool, "retry_budget", 2)
            
            while True:
                tool_start = time.time()
                res = await tool.execute(db, state.user_id, args)
                tool_latency = time.time() - tool_start
                state.metrics["tool_latency"] += tool_latency
                
                # Check status
                if res.get("status") == "success":
                    tool_memory.record_execution(tool.name, success=True)
                    # Record Fact Evidence in Blackboard
                    fact_id = f"fact_{tool.name}_{int(time.time())}"
                    state.blackboard.evidence_graph[fact_id] = Evidence(
                        fact_id=fact_id,
                        source_type="connector",
                        source_ref=tool.name,
                        confidence_score=getattr(tool, "reliability", 0.95),
                        verified_by=["tool_success"]
                    )
                    return res
                    
                # Action failed! Log statistics
                tool_memory.record_execution(tool.name, success=False)
                classification = res.get("failure_classification", "PERMANENT")
                
                if classification == "RATE_LIMITED":
                    tool_memory.mark_rate_limited(tool.name)
                elif classification == "RETRYABLE" and retry_count >= max_retries:
                    tool_memory.mark_offline(tool.name)
                
                if classification == "RETRYABLE" and retry_count < max_retries:
                    retry_count += 1
                    state.metrics["retry_count"] += 1
                    logger.info(f"Retrying tool {tool.name} (attempt {retry_count}/{max_retries}) due to retryable error: {res.get('message')}")
                    await asyncio.sleep(0.5)
                    continue
                    
                # 3. Alternate Tool Fallback (Capability Routing)
                alternate_tool = None
                for t in tool_registry.list_tools():
                    if t.name != tool.name and target in getattr(t, "capabilities", []):
                        alternate_tool = t
                        break
                        
                if alternate_tool:
                    logger.info(f"Escalating to alternate tool: {alternate_tool.name} for capability {target}")
                    tool = alternate_tool
                    retry_count = 0
                    max_retries = getattr(tool, "retry_budget", 2)
                    continue
                    
                # 4. Alternate Query Fallback (broaden filters)
                if "query" in args:
                    old_query = args["query"]
                    words = old_query.split()
                    if len(words) > 1:
                        new_query = " ".join(words[:-1])
                        logger.info(f"Broadening search query from '{old_query}' to '{new_query}'")
                        args["query"] = new_query
                        retry_count = 0
                        continue
                        
                # 5. Escalate to HIL Clarification
                state.status = "clarifying"
                state.clarification_pending = True
                state.clarification_question = f"Execution failed for tool '{tool.name}'. Could you please clarify your goal?"
                return res

        execution_promises = [_execute_single_action(item) for item in resolved_tools]
        responses = await asyncio.gather(*execution_promises)
        parallel_time = time.time() - loop_start
        state.metrics["parallel_execution_time"] += parallel_time
        
        return {
            "responses": responses,
            "actions_run": [{"tool": r["tool"].name if r["tool"] else r["target"], "args": r["args"], "version": r["tool"].version if r["tool"] else "0.0.0"} for r in resolved_tools]
        }

    async def route(self, db: Session, user_id: int, user_role: str, session_id: str, query: str) -> Dict[str, Any]:
        """
        Stateful loop coordinator with resumption from clarification flow.
        """
        loop_start_time = time.time()
        
        history_record = db.query(AgentExecutionHistory).filter(
            AgentExecutionHistory.session_id == session_id
        ).first()
        
        state = None
        if history_record and history_record.plan_dag:
            try:
                state_dict = history_record.plan_dag
                state = JobAgentState.model_validate(state_dict)
                
                if state.clarification_pending:
                    state.world_state["known_facts"].append(f"User clarified: {query}")
                    if state.blackboard:
                        state.blackboard.known_facts.append(f"User clarified: {query}")
                    state.clarification_pending = False
                    state.clarification_question = None
                    state.interactive_card = None
                    state.status = "pending"
            except Exception as e:
                logger.error(f"Failed to deserialize JobAgentState: {e}")
                state = None
                
        if not state:
            state = JobAgentState(
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                query=query,
                main_goal=query
            )
            
        if not state.blackboard:
            state.blackboard = Blackboard(session_id=session_id)
            
        if not history_record:
            history_record = AgentExecutionHistory(
                user_id=user_id,
                session_id=session_id,
                plan_dag=state.model_dump(mode="json"),
                execution_steps=[],
                confidence_score=1.0,
                status="pending"
            )
            db.add(history_record)
            db.commit()
            db.refresh(history_record)
            
        latest_updates = []
        
        while state.status == "pending":
            state.iteration_count += 1
            
            if state.iteration_count > state.max_iterations:
                state.status = "failed"
                break
                
            # Think
            think_data = await self.think(state, db)
            if not think_data:
                state.status = "failed"
                break
                
            state.current_thought = think_data.get("thought", "Thinking...")
            latest_updates = think_data.get("progress_updates", ["Processing..."])
            
            goal_data = think_data.get("goal_stack", {})
            state.main_goal = goal_data.get("main_goal", state.main_goal)
            state.subgoal = goal_data.get("subgoal", state.subgoal)
            state.current_task = goal_data.get("current_task", state.current_task)
            
            # Map LLM Blackboard to State Blackboard
            bb_data = think_data.get("blackboard", {})
            if bb_data:
                state.blackboard = Blackboard.model_validate(bb_data)
                # Sync world_state for legacy compatibility
                state.world_state["known_facts"] = state.blackboard.known_facts
                state.world_state["unknown_facts"] = state.blackboard.unknown_facts
                state.world_state["assumptions"] = state.blackboard.assumptions
                state.world_state["blocked_items"] = state.blackboard.blocked_items
                state.world_state["completed_tasks"] = state.blackboard.completed_tasks
                state.world_state["pending_tasks"] = state.blackboard.pending_tasks
            
            next_actions = think_data.get("next_actions", [])
            confidence = think_data.get("confidence", 1.0)
            clarification_question = think_data.get("clarification_question")
            state.interactive_card = think_data.get("interactive_card")
            
            # Confidence clarification check
            if (confidence < 0.75 or state.clarification_pending) and next_actions:
                state.status = "clarifying"
                state.clarification_pending = True
                state.clarification_question = clarification_question or state.clarification_question or "Could you clarify your request?"
                break
                
            has_finish = any(a.get("tool_or_capability") == "finish" for a in next_actions)
            if has_finish or not next_actions:
                state.status = "completed"
                break
                
            # Act: Capability Resolution & concurrent execution with Escalation recovery
            act_results = await self.execute_actions_with_escalation(state, next_actions, db)
            responses = act_results["responses"]
            actions_run = act_results["actions_run"]
            
            # Observe & Reflect
            state.last_observation = responses
            
            step_record = {
                "iteration": state.iteration_count,
                "thought": state.current_thought,
                "progress_updates": latest_updates,
                "actions": actions_run,
                "responses": responses,
                "timestamp": datetime.utcnow().isoformat()
            }
            state.execution_steps.append(step_record)
            state.metrics["reflection_count"] += 1
            
            history_record.execution_steps = state.execution_steps
            history_record.plan_dag = state.model_dump(mode="json")
            history_record.confidence_score = confidence
            history_record.status = state.status
            db.commit()
            
            await event_bus.publish("telemetry", {
                "session_id": session_id,
                "progress_updates": latest_updates,
                "status": state.status,
                "steps": len(state.execution_steps)
            })
            
        state.metrics["total_latency"] = time.time() - loop_start_time
        
        history_record.plan_dag = state.model_dump(mode="json")
        history_record.status = state.status
        db.commit()
        
        return {
            "status": state.status,
            "session_id": session_id,
            "clarification_question": state.clarification_question,
            "interactive_card": state.interactive_card,
            "progress_updates": latest_updates,
            "steps_executed": state.execution_steps,
            "final_response": state.last_observation,
            "metrics": state.metrics
        }

supervisor_agent = SupervisorAgent()
