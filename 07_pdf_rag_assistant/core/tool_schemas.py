"""
Tool schemas for OpenAI function calling
Defines how the LLM should call each tool
"""

from typing import List, Dict, Any

# =============================================================================
# TOOL SCHEMAS
# =============================================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search through uploaded PDF documents using advanced hybrid RAG pipeline. Use this when users ask questions about document content, want to find information in PDFs, or need document analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question about the documents. Can be specific questions, general topics, or comparison requests."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_documents",
            "description": "List all currently loaded PDF documents with their statistics including chunk counts, page ranges, and document names. Use this when users want to know what documents are available or get document statistics.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_percentage",
            "description": "Calculate what percentage a value represents of a total. Useful for analyzing proportions, ratios, or parts of a whole.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "The value to calculate percentage for"
                    },
                    "total": {
                        "type": "number",
                        "description": "The total value (represents 100%)"
                    }
                },
                "required": ["value", "total"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_salary_increment",
            "description": "Calculate salary increment amount and percentage increase/decrease between old and new salary amounts. Useful for HR calculations and salary analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_salary": {
                        "type": "number",
                        "description": "The previous/old salary amount"
                    },
                    "new_salary": {
                        "type": "number",
                        "description": "The new/updated salary amount"
                    }
                },
                "required": ["old_salary", "new_salary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather information for a specified city including temperature, conditions, and humidity. Note: This is a mock service with sample data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city to get weather for (e.g., 'Bangalore', 'Mumbai', 'Delhi')"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert currency amounts between different currencies using exchange rates. Note: This uses mock exchange rates for demonstration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The amount to convert"
                    },
                    "from_currency": {
                        "type": "string",
                        "description": "Source currency code (e.g., 'USD', 'INR', 'EUR', 'GBP')"
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "Target currency code (e.g., 'USD', 'INR', 'EUR', 'GBP')"
                    }
                },
                "required": ["amount", "from_currency", "to_currency"]
            }
        }
    }
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tool_schemas() -> List[Dict[str, Any]]:
    """Get all tool schemas for OpenAI function calling"""
    return TOOL_SCHEMAS

def get_tool_schema_by_name(tool_name: str) -> Dict[str, Any]:
    """Get specific tool schema by name"""
    for schema in TOOL_SCHEMAS:
        if schema["function"]["name"] == tool_name:
            return schema
    return None

def get_available_tool_names() -> List[str]:
    """Get list of all available tool names"""
    return [schema["function"]["name"] for schema in TOOL_SCHEMAS]

def get_tool_descriptions() -> Dict[str, str]:
    """Get mapping of tool names to their descriptions"""
    return {
        schema["function"]["name"]: schema["function"]["description"] 
        for schema in TOOL_SCHEMAS
    }