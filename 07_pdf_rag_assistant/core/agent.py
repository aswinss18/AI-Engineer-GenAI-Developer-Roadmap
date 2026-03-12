"""
AI Agent system with ReAct pattern for better performance
"""

import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from .tools import get_tool_function, execute_tool_from_registry, TOOLS_REGISTRY
from .tool_schemas import get_tool_schemas
import os

logger = logging.getLogger(__name__)

class AIAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        self.tools = get_tool_schemas()
        
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given arguments (legacy method)
        """
        return execute_tool_from_registry(tool_name, arguments)
    
    def run_agent_react(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None, max_steps: int = 5) -> Dict[str, Any]:
        """
        Run ReAct agent with iterative reasoning and tool calling
        
        Args:
            query: User query
            conversation_history: Optional conversation history
            max_steps: Maximum reasoning steps to prevent infinite loops
            
        Returns:
            Agent response with reasoning steps and final answer
        """
        try:
            # Build initial messages
            messages = []
            
            # System message for ReAct pattern
            system_message = {
                "role": "system",
                "content": """You are an intelligent ReAct agent with access to various tools. You can:

1. Search and analyze PDF documents using advanced hybrid RAG pipeline
2. Perform calculations (percentages, salary increments, etc.)
3. Get weather information for cities
4. Convert currencies between different denominations
5. List and manage document information

REACT PATTERN - Think step by step and use multiple tools when needed:

CRITICAL: When users ask about temperature, weather, or "how hot" someone feels:
1. FIRST: Search documents to find their location
2. THEN: Use get_weather tool to get current temperature for that location
3. FINALLY: Combine both results in your answer

CRITICAL: When users ask about calculations involving document data:
1. FIRST: Search documents to find the numbers
2. THEN: Use calculation tools to compute the result
3. FINALLY: Explain the calculation

For complex queries, break them down:
- "How hot does X feel?" → search_documents (find location) → get_weather (get temperature)
- "Calculate Y% of salary" → search_documents (find salary) → calculate_percentage (compute result)
- "Weather where X lives" → search_documents (find location) → get_weather (get temperature)

IMPORTANT: Always use tools in sequence when the query requires multiple steps. Don't stop after just one tool if more information is needed.

Available tools: search_documents, list_available_documents, calculate_percentage, calculate_salary_increment, get_weather, convert_currency

Be concise, accurate, and always use the appropriate tools to get complete information."""
            }
            messages.append(system_message)
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user query
            messages.append({"role": "user", "content": query})
            
            tool_results = []
            reasoning_steps = []
            
            # ReAct loop - iterative reasoning and acting
            for step in range(max_steps):
                logger.info(f"ReAct Step {step + 1}: Processing query")
                
                # LLM reasoning and tool selection
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                
                # Add assistant's response to messages
                messages.append(response_message)
                
                # If no tools called, we have final answer
                if not tool_calls:
                    logger.info(f"ReAct completed in {step + 1} steps - Final answer ready")
                    final_answer = response_message.content
                    break
                
                # Execute tools and observe results
                logger.info(f"ReAct Step {step + 1}: Executing {len(tool_calls)} tool(s)")
                step_tools = []
                
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool arguments: {e}")
                        arguments = {}
                    
                    # Execute tool using registry
                    tool_result = execute_tool_from_registry(tool_name, arguments)
                    
                    step_tool = {
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": tool_result
                    }
                    step_tools.append(step_tool)
                    tool_results.append(step_tool)
                    
                    # Add tool result to messages for next reasoning step
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                
                reasoning_steps.append({
                    "step": step + 1,
                    "tools_used": step_tools,
                    "reasoning": "Tool execution and observation"
                })
                
            else:
                # Max steps reached, generate final response
                logger.warning(f"ReAct reached max steps ({max_steps}), generating final response")
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                final_answer = final_response.choices[0].message.content
            
            return {
                "success": True,
                "query": query,
                "answer": final_answer,
                "tools_used": len(tool_results),
                "tool_calls": tool_results,
                "reasoning_steps": reasoning_steps,
                "has_tool_calls": bool(tool_results),
                "react_pattern": True
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
                "react_pattern": True
            }

    def run_agent(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Legacy method - now uses ReAct pattern for better performance
        """
        return self.run_agent_react(query, conversation_history)
    
    def run_agent_stream(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None):
        """
        Run agent with streaming response using ReAct pattern
        
        Args:
            query: User query
            conversation_history: Optional conversation history
            
        Yields:
            Streaming response chunks
        """
        try:
            # For ReAct tool calling, we need to do the full execution first, then stream the result
            result = self.run_agent_react(query, conversation_history)
            
            if result["success"]:
                # Stream the final answer
                answer = result["answer"]
                
                # First yield metadata with ReAct info
                yield {
                    "type": "metadata",
                    "tools_used": result["tools_used"],
                    "tool_calls": result["tool_calls"],
                    "has_tool_calls": result["has_tool_calls"],
                    "reasoning_steps": result.get("reasoning_steps", []),
                    "react_pattern": result.get("react_pattern", True)
                }
                
                # Then stream the answer in chunks
                chunk_size = 50  # Characters per chunk
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i + chunk_size]
                    yield {
                        "type": "content",
                        "content": chunk
                    }
                
                # Final completion signal
                yield {
                    "type": "done",
                    "complete": True
                }
            else:
                # Error case
                yield {
                    "type": "error",
                    "error": result["error"],
                    "content": result["answer"]
                }
                
        except Exception as e:
            logger.error(f"Streaming ReAct agent execution failed: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "content": "I apologize, but I encountered an error while processing your request."
            }

# Global agent instance
agent = AIAgent()

def run_agent(query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Convenience function to run the ReAct agent"""
    return agent.run_agent(query, conversation_history)

def run_agent_stream(query: str, conversation_history: Optional[List[Dict[str, str]]] = None):
    """Convenience function to run the ReAct agent with streaming"""
    return agent.run_agent_stream(query, conversation_history)