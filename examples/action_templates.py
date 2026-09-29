#!/usr/bin/env python3
"""
Example Action Templates for MCP Server

This script provides ready-to-use action templates that can be imported
into your MCP server for common use cases.
"""

# Weather action using OpenWeatherMap API
WEATHER_ACTION = {
    "name": "get_weather",
    "type": "REST",
    "description": "Get current weather for any city",
    "enabled": True,
    "configuration": {
        "url": "https://api.openweathermap.org/data/2.5/weather?q={{city}}&appid={{openweather_api_key}}&units=metric",
        "method": "GET",
        "headers": {
            "Accept": "application/json"
        }
    }
}

# Calculator action for mathematical expressions
CALCULATOR_ACTION = {
    "name": "calculate",
    "type": "CODE_RUN",
    "description": "Perform mathematical calculations and expressions",
    "enabled": True,
    "configuration": {
        "code": """
import math
import statistics

# The user's expression is available as 'expression'
result = eval(expression, {"__builtins__": {}}, {
    "math": math,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "len": len,
    "mean": statistics.mean,
    "median": statistics.median,
    "stdev": statistics.stdev
})

print(f"Result: {result}")
"""
    }
}

# Web search using DuckDuckGo
SEARCH_ACTION = {
    "name": "web_search",
    "type": "REST",
    "description": "Search the web using DuckDuckGo",
    "enabled": True,
    "configuration": {
        "url": "https://api.duckduckgo.com/?q={{query}}&format=json&no_redirect=1&no_html=1",
        "method": "GET",
        "headers": {
            "Accept": "application/json"
        }
    }
}

# GitHub repository search
GITHUB_SEARCH_ACTION = {
    "name": "github_search",
    "type": "REST",
    "description": "Search GitHub repositories",
    "enabled": True,
    "configuration": {
        "url": "https://api.github.com/search/repositories?q={{query}}&sort=stars&order=desc",
        "method": "GET",
        "headers": {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": "Bearer {{github_token}}"
        }
    }
}

# Text analysis action
TEXT_ANALYSIS_ACTION = {
    "name": "analyze_text",
    "type": "CODE_RUN",
    "description": "Analyze text for word count, readability, and basic statistics",
    "enabled": True,
    "configuration": {
        "code": """
import re
from collections import Counter

# The user's text is available as 'text'
words = text.split()
sentences = re.split(r'[.!?]+', text)
sentences = [s.strip() for s in sentences if s.strip()]

# Basic statistics
word_count = len(words)
sentence_count = len(sentences)
avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

# Most common words
word_freq = Counter(word.lower() for word in words if len(word) > 3)
top_words = word_freq.most_common(5)

print(f"Word count: {word_count}")
print(f"Sentence count: {sentence_count}")
print(f"Average word length: {avg_word_length:.1f} characters")
print(f"Average sentence length: {avg_sentence_length:.1f} words")
print(f"\\nTop 5 words:")
for word, count in top_words:
    print(f"  - {word}: {count}")
"""
    }
}

# JSON formatter action
JSON_FORMATTER_ACTION = {
    "name": "format_json",
    "type": "CODE_RUN",
    "description": "Format and validate JSON data",
    "enabled": True,
    "configuration": {
        "code": """
import json

# The user's JSON string is available as 'json_string'
try:
    # Parse the JSON
    data = json.loads(json_string)
    
    # Pretty print with indentation
    formatted = json.dumps(data, indent=2, sort_keys=True)
    print(formatted)
    
    # Basic statistics
    print(f"\\n--- JSON Statistics ---")
    if isinstance(data, dict):
        print(f"Keys: {len(data)}")
        print(f"Key names: {', '.join(data.keys())}")
    elif isinstance(data, list):
        print(f"Items: {len(data)}")
        
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
"""
    }
}

# URL shortener using is.gd
URL_SHORTENER_ACTION = {
    "name": "shorten_url",
    "type": "REST",
    "description": "Shorten long URLs using is.gd service",
    "enabled": True,
    "configuration": {
        "url": "https://is.gd/create.php?format=json&url={{url}}",
        "method": "GET",
        "headers": {
            "Accept": "application/json"
        }
    }
}

# All templates
ALL_TEMPLATES = [
    WEATHER_ACTION,
    CALCULATOR_ACTION,
    SEARCH_ACTION,
    GITHUB_SEARCH_ACTION,
    TEXT_ANALYSIS_ACTION,
    JSON_FORMATTER_ACTION,
    URL_SHORTENER_ACTION
]

if __name__ == "__main__":
    # Print all templates
    import json
    for template in ALL_TEMPLATES:
        print(f"\n# {template['name']} - {template['description']}")
        print(json.dumps(template, indent=2))