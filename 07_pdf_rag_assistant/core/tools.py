"""
AI-callable tools for the agent system
"""

import logging
from typing import Dict, Any, List
from .rag_pipeline import ask_question as rag_search
from .vector_store import documents
from .multi_document_context import group_chunks_by_document, analyze_document_distribution

logger = logging.getLogger(__name__)

# =============================================================================
# DOCUMENT TOOLS
# =============================================================================

def search_documents(query: str) -> Dict[str, Any]:
    """
    Search through uploaded PDF documents using hybrid RAG pipeline
    
    Args:
        query: The search query or question about the documents
        
    Returns:
        Dictionary with search results and metadata
    """
    try:
        if not documents:
            return {
                "success": False,
                "error": "No documents are currently loaded. Please upload PDF documents first.",
                "answer": None,
                "document_count": 0
            }
        
        # Use the existing RAG pipeline
        answer = rag_search(query)
        
        # Get document statistics
        unique_docs = set(chunk.get("doc", "unknown") for chunk in documents)
        
        return {
            "success": True,
            "answer": answer,
            "document_count": len(unique_docs),
            "total_chunks": len(documents),
            "documents": list(unique_docs),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Error in document search: {e}")
        return {
            "success": False,
            "error": f"Document search failed: {str(e)}",
            "answer": None,
            "document_count": len(set(chunk.get("doc", "unknown") for chunk in documents)) if documents else 0
        }

def list_available_documents() -> Dict[str, Any]:
    """
    List all currently loaded documents with their statistics
    
    Returns:
        Dictionary with document information
    """
    try:
        if not documents:
            return {
                "success": True,
                "message": "No documents are currently loaded.",
                "documents": {},
                "total_documents": 0,
                "total_chunks": 0
            }
        
        # Group documents and get statistics
        doc_info = {}
        for chunk in documents:
            doc_name = chunk.get("doc", "unknown")
            if doc_name not in doc_info:
                doc_info[doc_name] = {
                    "chunk_count": 0,
                    "pages": set()
                }
            doc_info[doc_name]["chunk_count"] += 1
            doc_info[doc_name]["pages"].add(chunk.get("page", 0))
        
        # Convert sets to sorted lists and add page ranges
        for doc_name in doc_info:
            pages = sorted(list(doc_info[doc_name]["pages"]))
            doc_info[doc_name]["pages"] = pages
            doc_info[doc_name]["page_range"] = f"{min(pages)}-{max(pages)}" if pages else "unknown"
            doc_info[doc_name]["total_pages"] = len(pages)
        
        return {
            "success": True,
            "documents": doc_info,
            "total_documents": len(doc_info),
            "total_chunks": len(documents),
            "message": f"Found {len(doc_info)} documents with {len(documents)} total chunks."
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {
            "success": False,
            "error": f"Failed to list documents: {str(e)}",
            "documents": {},
            "total_documents": 0,
            "total_chunks": 0
        }

# =============================================================================
# UTILITY TOOLS
# =============================================================================

def calculate_percentage(value: float, total: float) -> Dict[str, Any]:
    """
    Calculate percentage of a value relative to a total
    
    Args:
        value: The value to calculate percentage for
        total: The total value (100%)
        
    Returns:
        Dictionary with calculation results
    """
    try:
        if total == 0:
            return {
                "success": False,
                "error": "Cannot calculate percentage: total cannot be zero",
                "percentage": None
            }
        
        percentage = (value / total) * 100
        
        return {
            "success": True,
            "value": value,
            "total": total,
            "percentage": round(percentage, 2),
            "formatted": f"{round(percentage, 2)}%"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Calculation failed: {str(e)}",
            "percentage": None
        }

def calculate_salary_increment(old_salary: float, new_salary: float) -> Dict[str, Any]:
    """
    Calculate salary increment amount and percentage
    
    Args:
        old_salary: Previous salary amount
        new_salary: New salary amount
        
    Returns:
        Dictionary with increment calculations
    """
    try:
        if old_salary <= 0:
            return {
                "success": False,
                "error": "Old salary must be greater than zero",
                "increment": None,
                "percentage": None
            }
        
        increment = new_salary - old_salary
        percentage = (increment / old_salary) * 100
        
        return {
            "success": True,
            "old_salary": old_salary,
            "new_salary": new_salary,
            "increment": round(increment, 2),
            "percentage": round(percentage, 2),
            "is_increase": increment > 0,
            "formatted_increment": f"+{increment}" if increment > 0 else str(increment),
            "formatted_percentage": f"{round(percentage, 2)}%"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Salary calculation failed: {str(e)}",
            "increment": None,
            "percentage": None
        }

def get_weather(city: str) -> Dict[str, Any]:
    """
    Get weather information for a city (mock implementation)
    
    Args:
        city: Name of the city
        
    Returns:
        Dictionary with weather information
    """
    # Mock weather data - in real implementation, this would call a weather API
    mock_weather_data = {
        "bangalore": {"temperature": 29, "condition": "Cloudy", "humidity": 65},
        "mumbai": {"temperature": 32, "condition": "Sunny", "humidity": 78},
        "delhi": {"temperature": 35, "condition": "Hot", "humidity": 45},
        "chennai": {"temperature": 31, "condition": "Humid", "humidity": 82},
        "kolkata": {"temperature": 28, "condition": "Rainy", "humidity": 88},
        "hyderabad": {"temperature": 30, "condition": "Partly Cloudy", "humidity": 60},
        "pune": {"temperature": 27, "condition": "Pleasant", "humidity": 55},
        "ahmedabad": {"temperature": 36, "condition": "Very Hot", "humidity": 40}
    }
    
    city_lower = city.lower()
    
    if city_lower in mock_weather_data:
        weather = mock_weather_data[city_lower]
        return {
            "success": True,
            "city": city.title(),
            "temperature": weather["temperature"],
            "condition": weather["condition"],
            "humidity": weather["humidity"],
            "unit": "Celsius",
            "message": f"Weather in {city.title()}: {weather['temperature']}°C, {weather['condition']}"
        }
    else:
        # Default weather for unknown cities
        return {
            "success": True,
            "city": city.title(),
            "temperature": 25,
            "condition": "Unknown",
            "humidity": 50,
            "unit": "Celsius",
            "message": f"Weather data for {city.title()} is not available. Showing default values.",
            "note": "This is a mock weather service. For real weather data, integrate with a weather API."
        }

def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    """
    Convert currency amounts (mock implementation with fixed rates)
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., 'USD')
        to_currency: Target currency code (e.g., 'INR')
        
    Returns:
        Dictionary with conversion results
    """
    # Mock exchange rates (in real implementation, use live rates)
    exchange_rates = {
        "USD": {"INR": 83.0, "EUR": 0.85, "GBP": 0.73, "JPY": 110.0},
        "INR": {"USD": 0.012, "EUR": 0.010, "GBP": 0.009, "JPY": 1.33},
        "EUR": {"USD": 1.18, "INR": 98.0, "GBP": 0.86, "JPY": 130.0},
        "GBP": {"USD": 1.37, "INR": 114.0, "EUR": 1.16, "JPY": 151.0}
    }
    
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    try:
        if from_currency == to_currency:
            return {
                "success": True,
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "converted_amount": amount,
                "exchange_rate": 1.0,
                "message": f"No conversion needed: {amount} {from_currency}"
            }
        
        if from_currency not in exchange_rates or to_currency not in exchange_rates[from_currency]:
            return {
                "success": False,
                "error": f"Exchange rate not available for {from_currency} to {to_currency}",
                "supported_currencies": list(exchange_rates.keys())
            }
        
        rate = exchange_rates[from_currency][to_currency]
        converted_amount = amount * rate
        
        return {
            "success": True,
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "converted_amount": round(converted_amount, 2),
            "exchange_rate": rate,
            "message": f"{amount} {from_currency} = {round(converted_amount, 2)} {to_currency}",
            "note": "Using mock exchange rates. For real rates, integrate with a currency API."
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Currency conversion failed: {str(e)}",
            "converted_amount": None
        }

# =============================================================================
# TOOL REGISTRY
# =============================================================================

# Available tools registry
AVAILABLE_TOOLS = {
    "search_documents": search_documents,
    "list_available_documents": list_available_documents,
    "calculate_percentage": calculate_percentage,
    "calculate_salary_increment": calculate_salary_increment,
    "get_weather": get_weather,
    "convert_currency": convert_currency
}

def get_tool_function(tool_name: str):
    """Get tool function by name"""
    return AVAILABLE_TOOLS.get(tool_name)

def list_available_tools() -> List[str]:
    """Get list of available tool names"""
    return list(AVAILABLE_TOOLS.keys())