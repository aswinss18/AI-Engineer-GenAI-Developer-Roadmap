"""
Central tool registry for the ReAct agent.
Combines document tools and utility tools, provides execution with error handling.
"""

import logging
from typing import Dict, Any, List
from app.tools.document_tools import search_documents, list_available_documents
from app.tools.utility_tools import (
    calculate_percentage,
    calculate_salary_increment,
    get_weather,
    convert_currency,
)

logger = logging.getLogger(__name__)

TOOLS_REGISTRY: Dict[str, Any] = {
    "search_documents": search_documents,
    "list_available_documents": list_available_documents,
    "calculate_percentage": calculate_percentage,
    "calculate_salary_increment": calculate_salary_increment,
    "get_weather": get_weather,
    "convert_currency": convert_currency,
}

# Legacy alias
AVAILABLE_TOOLS = TOOLS_REGISTRY


def get_tool_function(tool_name: str):
    """Get tool function by name."""
    return TOOLS_REGISTRY.get(tool_name)


def list_available_tools() -> List[str]:
    """Get list of available tool names."""
    return list(TOOLS_REGISTRY.keys())


def execute_tool_from_registry(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool from the registry with error handling."""
    try:
        tool_function = TOOLS_REGISTRY.get(tool_name)
        if not tool_function:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry",
                "available_tools": list(TOOLS_REGISTRY.keys()),
            }
        return tool_function(**arguments)
    except Exception as e:
        logger.error(f"Tool execution failed [{tool_name}]: {e}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "tool_name": tool_name,
            "arguments": arguments,
        }
