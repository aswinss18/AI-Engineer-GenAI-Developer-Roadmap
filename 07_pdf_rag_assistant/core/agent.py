"""
AI Agent system with tool calling capabilities
"""

import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from .tools import get_tool_function
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
        Execute a tool with given arguments
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        try:
            tool_function = get_tool_function(tool_name)
            if not tool_function:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                    "available_tools": list(self.tools)
                }
            
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
            result = tool_function(**arguments)
            logger.info(f"Tool {tool_name} executed successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name,
                "arguments": arguments
            }
    
    def run_agent(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Run the agent with tool calling capabilities
        
        Args:
            query: User query
            conversation_history: Optional conversation history
            
        Returns:
            Agent response with tool calls and final answer
        """
        try:
            # Build messages
            messages = []
            
            # System message
            system_message = {
                "role": "system",
                "content": """You are an intelligent AI assistant with access to various tools. You can:

1. Search and analyze PDF documents using advanced hybrid RAG pipeline
2. Perform calculations (percentages, salary increments, etc.)
3. Get weather information for cities
4. Convert currencies between different denominations
5. List and manage document information

When a user asks a question:
- If it's about document content, use the search_documents tool
- If they want to know what documents are available, use list_available_documents
- If they need calculations, use the appropriate calculation tools
- If they ask about weather, use the get_weather tool
- If they need currency conversion, use the convert_currency tool

IMPORTANT: You can use multiple tools in sequence to answer complex questions. For example:
- If someone asks about the weather where a person lives, first search documents to find their location, then get weather for that location
- If someone asks to calculate a percentage of a salary mentioned in documents, first search for the salary amount, then calculate the percentage

Always use the most appropriate tool(s) for the user's request. If no tool is needed, respond directly.

Be helpful, accurate, and provide clear explanations of the results."""
            }
            messages.append(system_message)
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user query
            messages.append({"role": "user", "content": query})
            
            # First LLM call to determine if tools are needed
            logger.info(f"Processing query: {query}")
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
            
            tool_results = []
            
            # Execute tools if any were called
            if tool_calls:
                logger.info(f"LLM requested {len(tool_calls)} tool calls")
                
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool arguments: {e}")
                        arguments = {}
                    
                    # Execute the tool
                    tool_result = self.execute_tool(tool_name, arguments)
                    tool_results.append({
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": tool_result
                    })
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                
                # Second LLM call to generate final response with tool results
                # This call might also request additional tools
                logger.info("Generating response with tool results")
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                
                final_response_message = final_response.choices[0].message
                additional_tool_calls = final_response_message.tool_calls
                
                # Add the assistant's response to messages
                messages.append(final_response_message)
                
                # Handle additional tool calls if any
                if additional_tool_calls:
                    logger.info(f"LLM requested {len(additional_tool_calls)} additional tool calls")
                    
                    for tool_call in additional_tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse tool arguments: {e}")
                            arguments = {}
                        
                        # Execute the additional tool
                        tool_result = self.execute_tool(tool_name, arguments)
                        tool_results.append({
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result
                        })
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result)
                        })
                    
                    # Final LLM call to generate the complete response
                    logger.info("Generating final response with all tool results")
                    complete_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages
                    )
                    
                    final_answer = complete_response.choices[0].message.content
                else:
                    # No additional tools needed
                    final_answer = final_response_message.content
                
            else:
                # No tools needed, use direct response
                logger.info("No tools needed, using direct response")
                final_answer = response_message.content
            
            return {
                "success": True,
                "query": query,
                "answer": final_answer,
                "tools_used": len(tool_results),
                "tool_calls": tool_results,
                "has_tool_calls": bool(tool_results)
            }
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "success": False,
                "error": f"Agent failed: {str(e)}",
                "query": query,
                "answer": "I apologize, but I encountered an error while processing your request. Please try again.",
                "tools_used": 0,
                "tool_calls": [],
                "has_tool_calls": False
            }
    
    def run_agent_stream(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None):
        """
        Run agent with streaming response (for tool calls, we need to handle differently)
        
        Args:
            query: User query
            conversation_history: Optional conversation history
            
        Yields:
            Streaming response chunks
        """
        try:
            # For tool calling, we need to do the full execution first, then stream the result
            result = self.run_agent(query, conversation_history)
            
            if result["success"]:
                # Stream the final answer
                answer = result["answer"]
                
                # First yield metadata
                yield {
                    "type": "metadata",
                    "tools_used": result["tools_used"],
                    "tool_calls": result["tool_calls"],
                    "has_tool_calls": result["has_tool_calls"]
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
            logger.error(f"Streaming agent execution failed: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "content": "I apologize, but I encountered an error while processing your request."
            }

# Global agent instance
agent = AIAgent()

def run_agent(query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Convenience function to run the agent"""
    return agent.run_agent(query, conversation_history)

def run_agent_stream(query: str, conversation_history: Optional[List[Dict[str, str]]] = None):
    """Convenience function to run the agent with streaming"""
    return agent.run_agent_stream(query, conversation_history)