"""
Utility / calculation tools for the agent.
Moved from core/tools.py — no internal imports required.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculate_percentage(value: float, total: float) -> Dict[str, Any]:
    """Calculate percentage of a value relative to a total."""
    try:
        if total == 0:
            return {"success": False, "error": "Cannot calculate percentage: total cannot be zero", "percentage": None}
        percentage = (value / total) * 100
        return {
            "success": True,
            "value": value,
            "total": total,
            "percentage": round(percentage, 2),
            "formatted": f"{round(percentage, 2)}%",
        }
    except Exception as e:
        return {"success": False, "error": f"Calculation failed: {str(e)}", "percentage": None}


def calculate_salary_increment(old_salary: float, new_salary: float) -> Dict[str, Any]:
    """Calculate salary increment amount and percentage."""
    try:
        if old_salary <= 0:
            return {"success": False, "error": "Old salary must be greater than zero", "increment": None, "percentage": None}
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
            "formatted_percentage": f"{round(percentage, 2)}%",
        }
    except Exception as e:
        return {"success": False, "error": f"Salary calculation failed: {str(e)}", "increment": None, "percentage": None}


def get_weather(city: str) -> Dict[str, Any]:
    """Get weather information for a city (mock implementation)."""
    mock_weather_data = {
        "bangalore": {"temperature": 29, "condition": "Cloudy", "humidity": 65},
        "mumbai": {"temperature": 32, "condition": "Sunny", "humidity": 78},
        "delhi": {"temperature": 35, "condition": "Hot", "humidity": 45},
        "chennai": {"temperature": 31, "condition": "Humid", "humidity": 82},
        "kolkata": {"temperature": 28, "condition": "Rainy", "humidity": 88},
        "hyderabad": {"temperature": 30, "condition": "Partly Cloudy", "humidity": 60},
        "pune": {"temperature": 27, "condition": "Pleasant", "humidity": 55},
        "ahmedabad": {"temperature": 36, "condition": "Very Hot", "humidity": 40},
    }
    city_clean = city.lower().strip()
    if "," in city_clean:
        city_clean = city_clean.split(",")[0].strip()
    city_variations = {"bengaluru": "bangalore", "bombay": "mumbai", "calcutta": "kolkata", "madras": "chennai"}
    if city_clean in city_variations:
        city_clean = city_variations[city_clean]
    if city_clean in mock_weather_data:
        weather = mock_weather_data[city_clean]
        return {
            "success": True,
            "city": city.title(),
            "temperature": weather["temperature"],
            "condition": weather["condition"],
            "humidity": weather["humidity"],
            "unit": "Celsius",
            "message": f"Weather in {city.split(',')[0].strip()}: {weather['temperature']}°C, {weather['condition']}",
        }
    return {
        "success": True,
        "city": city.title(),
        "temperature": 25,
        "condition": "Unknown",
        "humidity": 50,
        "unit": "Celsius",
        "message": f"Weather data for {city.title()} is not available. Showing default values.",
        "note": "This is a mock weather service.",
    }


def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    """Convert currency amounts (mock implementation with fixed rates)."""
    exchange_rates = {
        "USD": {"INR": 83.0, "EUR": 0.85, "GBP": 0.73, "JPY": 110.0},
        "INR": {"USD": 0.012, "EUR": 0.010, "GBP": 0.009, "JPY": 1.33},
        "EUR": {"USD": 1.18, "INR": 98.0, "GBP": 0.86, "JPY": 130.0},
        "GBP": {"USD": 1.37, "INR": 114.0, "EUR": 1.16, "JPY": 151.0},
    }
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    try:
        if from_currency == to_currency:
            return {"success": True, "amount": amount, "from_currency": from_currency, "to_currency": to_currency, "converted_amount": amount, "exchange_rate": 1.0, "message": f"No conversion needed: {amount} {from_currency}"}
        if from_currency not in exchange_rates or to_currency not in exchange_rates.get(from_currency, {}):
            return {"success": False, "error": f"Exchange rate not available for {from_currency} to {to_currency}", "supported_currencies": list(exchange_rates.keys())}
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
            "note": "Using mock exchange rates.",
        }
    except Exception as e:
        return {"success": False, "error": f"Currency conversion failed: {str(e)}", "converted_amount": None}
