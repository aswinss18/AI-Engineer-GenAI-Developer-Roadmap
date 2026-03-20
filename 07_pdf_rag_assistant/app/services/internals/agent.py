"""
AI Agent system with ReAct pattern.
Moved from core/agent.py — imports updated to app package paths.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.tools.registry import execute_tool_from_registry, TOOLS_REGISTRY
from app.tools.schemas import get_tool_schemas
from app.services.internals.memory import (
    agent_memory,
    add_to_chat_history,
    get_chat_history,
    get_memory_context,
    extract_and_store_facts,
)
from app.services.internals.prompt_templates import build_optimized_prompt, optimize_memory
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIAgent:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.model_name
        self.tools = get_tool_schemas()

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return execute_tool_from_registry(tool_name, arguments)

    def run_agent_react(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 5,
    ) -> Dict[str, Any]:
        """Run ReAct agent with optimised prompt architecture."""
        try:
            raw_memory_context = get_memory_context(query)
            memory_data = None
            user_profile = "General user"

            if raw_memory_context:
                recent_memories = agent_memory.retrieve_memory(query, k=5)
                optimized_memories = optimize_memory(recent_memories, query)
                memory_data = optimized_memories
                if optimized_memories:
                    profile_parts = [
                        mem["text"]
                        for mem in optimized_memories[:2]
                        if "name" in mem.get("text", "").lower()
                    ]
                    user_profile = "; ".join(profile_parts) if profile_parts else "General user"

            available_tools = [
                "search_documents", "calculate_percentage", "calculate_salary_increment",
                "get_weather", "convert_currency", "list_available_documents",
            ]
            optimized_prompt = build_optimized_prompt(
                query=query, memory=memory_data, available_tools=available_tools, user_profile=user_profile
            )

            messages = [{"role": "system", "content": optimized_prompt}]

            if conversation_history:
                limited_history = (
                    conversation_history[-6:]
                    if len(conversation_history) > 6
                    else conversation_history
                )
                messages.extend(limited_history)
            else:
                chat_history = get_chat_history(max_messages=4)
                messages.extend(chat_history)

            messages.append({"role": "user", "content": query})
            add_to_chat_history("user", query)

            tool_results = []
            reasoning_steps = []
            final_answer = ""

            for step in range(max_steps):
                logger.info(f"ReAct Step {step + 1}: Processing query")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.1,
                )
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                messages.append(response_message)

                if not tool_calls:
                    logger.info(f"ReAct completed in {step + 1} steps")
                    final_answer = response_message.content
                    break

                logger.info(f"ReAct Step {step + 1}: Executing {len(tool_calls)} tool(s)")
                step_tools = []
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool arguments: {e}")
                        arguments = {}
                    tool_result = execute_tool_from_registry(tool_name, arguments)
                    if isinstance(tool_result, dict) and "answer" in tool_result:
                        answer = tool_result["answer"]
                        if len(answer) > 2000:
                            tool_result["answer"] = answer[:1997] + "..."
                    step_tool = {"tool_name": tool_name, "arguments": arguments, "result": tool_result}
                    step_tools.append(step_tool)
                    tool_results.append(step_tool)
                    tool_result_str = json.dumps(tool_result)
                    if len(tool_result_str) > 1500:
                        tool_result_str = tool_result_str[:1497] + "..."
                    messages.append(
                        {"role": "tool", "tool_call_id": tool_call.id, "content": tool_result_str}
                    )
                reasoning_steps.append(
                    {"step": step + 1, "tools_used": step_tools, "reasoning": "Tool execution and observation"}
                )
            else:
                logger.warning(f"ReAct reached max steps ({max_steps}), generating final response")
                final_response = self.client.chat.completions.create(
                    model=self.model, messages=messages, temperature=0.1
                )
                final_answer = final_response.choices[0].message.content

            add_to_chat_history("assistant", final_answer)
            extract_and_store_facts(query, final_answer)

            memory_context_info = None
            if raw_memory_context and memory_data:
                try:
                    memory_stats = agent_memory.get_memory_stats()
                    memory_context_info = {
                        "memories_retrieved": len(memory_data),
                        "memories_used": [
                            {
                                "text": mem["text"][:80] + "..." if len(mem["text"]) > 80 else mem["text"],
                                "importance": mem.get("importance", 0.5),
                                "confidence": mem.get("metadata", {}).get("confidence", "medium"),
                                "combined_score": mem.get("combined_score", 0.0),
                                "similarity_score": mem.get("similarity_score", 0.0),
                                "recency_score": mem.get("recency_score", 0.0),
                                "access_count": mem.get("access_count", 0),
                                "age_days": mem.get("age_days", 0),
                            }
                            for mem in memory_data[:3]
                        ],
                        "system_stats": {
                            "total_memories": memory_stats.get("stored_memories", 0),
                            "average_importance": memory_stats.get("average_importance", 0),
                            "quality_score": memory_stats.get("average_importance", 0) * 100,
                        },
                    }
                except Exception as e:
                    logger.error(f"Error getting memory context info: {e}")

            return {
                "success": True,
                "query": query,
                "answer": final_answer,
                "tools_used": len(tool_results),
                "tool_calls": tool_results,
                "reasoning_steps": reasoning_steps,
                "has_tool_calls": bool(tool_results),
                "react_pattern": True,
                "memory_used": bool(raw_memory_context),
                "memory_context_info": memory_context_info,
                "optimization_applied": True,
                "prompt_architecture": "modular_optimized",
            }

        except Exception as e:
            logger.error(f"ReAct agent execution failed: {e}")
            return {
                "success": False,
                "error": f"ReAct agent failed: {str(e)}",
                "query": query,
                "answer": "I apologize, but I encountered an error while processing your request. Please try again.",
                "tools_used": 0,
                "tool_calls": [],
                "reasoning_steps": [],
                "has_tool_calls": False,
                "react_pattern": True,
                "memory_used": False,
                "optimization_applied": True,
                "prompt_architecture": "modular_optimized",
            }

    def run_agent(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        return self.run_agent_react(query, conversation_history)

    def run_agent_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ):
        try:
            result = self.run_agent_react(query, conversation_history)
            if result["success"]:
                answer = result["answer"]
                yield {
                    "type": "metadata",
                    "tools_used": result["tools_used"],
                    "tool_calls": result["tool_calls"],
                    "has_tool_calls": result["has_tool_calls"],
                    "reasoning_steps": result.get("reasoning_steps", []),
                    "react_pattern": result.get("react_pattern", True),
                    "memory_used": result.get("memory_used", False),
                    "memory_context_info": result.get("memory_context_info"),
                }
                chunk_size = 50
                for i in range(0, len(answer), chunk_size):
                    yield {"type": "content", "content": answer[i: i + chunk_size]}
                yield {"type": "done", "complete": True}
            else:
                yield {"type": "error", "error": result["error"], "content": result["answer"]}
        except Exception as e:
            logger.error(f"Streaming ReAct agent execution failed: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "content": "I apologize, but I encountered an error while processing your request.",
            }


# Global agent instance
agent = AIAgent()


def run_agent(
    query: str, conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    return agent.run_agent(query, conversation_history)


def run_agent_stream(
    query: str, conversation_history: Optional[List[Dict[str, str]]] = None
):
    return agent.run_agent_stream(query, conversation_history)
