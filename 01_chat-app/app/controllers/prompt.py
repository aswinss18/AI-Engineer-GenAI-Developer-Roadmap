# prompts.py

BASE_SYSTEM_PROMPT = """
You are a precise AI assistant.
Always follow instructions carefully.
"""

SUMMARY_ROLE = """
You summarize content clearly and concisely.
"""

JSON_ENFORCER = """
Respond ONLY with valid JSON.
"""

def build_system_prompt(mode="default"):
    prompt = BASE_SYSTEM_PROMPT

    if mode == "summary":
        prompt += SUMMARY_ROLE

    if mode == "json":
        prompt += JSON_ENFORCER

    return prompt