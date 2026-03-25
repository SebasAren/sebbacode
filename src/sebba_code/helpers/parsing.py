"""Provides JSON and dict parsing utilities for LLM output extraction."""

import json
import re


def format_dict(d: dict) -> str:
    """Format a dict for inclusion in LLM prompts."""
    parts = []
    for k, v in d.items():
        if isinstance(v, dict):
            formatted = "\n".join(f"  {sk}: {sv}" for sk, sv in v.items())
            parts.append(f"### {k}\n{formatted}")
        else:
            parts.append(f"### {k}\n{v}")
    return "\n\n".join(parts)


def parse_json(text: str) -> dict:
    """Extract a JSON object from LLM output, handling code fences."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding the first { ... } block
    depth = 0
    start = None
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = None

    raise ValueError(f"Could not parse JSON from LLM output: {text[:200]}...")


def parse_json_list(text: str) -> list:
    """Extract a JSON list from LLM output."""
    text = text.strip()
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting from code fence
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Try finding [ ... ] block
    depth = 0
    start = None
    for i, c in enumerate(text):
        if c == "[":
            if depth == 0:
                start = i
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    result = json.loads(text[start : i + 1])
                    if isinstance(result, list):
                        return result
                except json.JSONDecodeError:
                    start = None

    raise ValueError(f"Could not parse JSON list from LLM output: {text[:200]}...")
