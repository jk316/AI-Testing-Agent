"""
Planner Agent - NL to DSL using Minimax
"""

import json
import re


PLANNER_PROMPT = """You are a Network Test Planner. Convert natural language test intent to structured DSL.

RULES:
- Extract target host/IP from the input
- Infer reasonable defaults for unspecified parameters
- Set stealth=true if user mentions stealth, quiet, silent, covert, or low rate
- Set scan=true if user mentions scan, port discovery
- Set stress=true if user mentions flood, ddos, stress, overwhelm
- Default port is 80 if scanning but not specified
- Default protocol is TCP if not specified
- Rate "low" means slow (1-10 pps), "medium" means normal (10-100 pps), "high" means fast (100-500 pps), "flood" means max speed

INPUT: {nl_input}

Return ONLY valid JSON matching this schema (no markdown, no explanation):
{{
  "target": "string (required)",
  "mode": "TCP | UDP | ICMP",
  "protocol": {{
    "type": "TCP | UDP | ICMP",
    "tcp_flags": ["SYN", "ACK", "FIN", "RST", "PSH", "URG"]
  }},
  "traffic": {{
    "rate": "low | medium | high | flood",
    "count": number or null,
    "interval": "string like u100, u1000, u10000 or null"
  }},
  "ports": {{
    "source": "string or null",
    "dest": "number or null"
  }},
  "ip": {{
    "ttl": "number or null",
    "spoof": "string or null",
    "random_source": "boolean",
    "fragment": "boolean"
  }},
  "intent": {{
    "stealth": "boolean",
    "scan": "boolean",
    "stress": "boolean",
    "firewall_test": "boolean",
    "performance": "boolean",
    "traceroute": "boolean",
    "fingerprint": "boolean"
  }},
  "assumptions": ["list of inferred defaults"]
}}"""


class PlannerAgent:
    def __init__(self, llm):
        self.llm = llm

    def parse(self, nl_input: str) -> dict:
        """Parse natural language to DSL"""
        # Extract target from input first as fallback
        extracted_target = self._extract_target(nl_input)

        prompt = PLANNER_PROMPT.format(nl_input=nl_input)

        response = self.llm([{"role": "user", "content": prompt}])

        # Extract JSON from response
        json_str = self._extract_json(response)

        result = json.loads(json_str)

        if isinstance(result, dict) and "assumptions" not in result:
            result["assumptions"] = []

        if isinstance(result, dict) and "protocol" in result:
            if isinstance(result["protocol"], dict) and "tcp_flags" not in result["protocol"]:
                result["protocol"]["tcp_flags"] = []

        # Ensure target is valid
        if not result.get("target") or result["target"] == "N/A" or result["target"] == "null":
            if extracted_target:
                result["target"] = extracted_target
                result.setdefault("assumptions", []).append(f"Target extracted from input: {extracted_target}")

        return result

    def _extract_target(self, text: str) -> str:
        """Extract IP or hostname from input"""
        # Try IP pattern
        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', text)
        if ip_match:
            return ip_match.group(1)
        # Try hostname pattern
        host_match = re.search(r'([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+)', text)
        if host_match:
            return host_match.group(1)
        # Last resort: get last word
        words = text.strip().split()
        return words[-1] if words else ""

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text"""
        # Try to find JSON block
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            json_str = match.group(0)
        else:
            # Try finding content between braces
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
            else:
                raise ValueError(f"Could not extract JSON from response: {text[:200]}")

        # Try to fix single quotes if json.loads fails
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # Try converting single quotes to double quotes
            import ast
            try:
                # Use ast.literal_eval to parse Python dict format
                parsed = ast.literal_eval(json_str)
                return json.dumps(parsed)
            except (ValueError, SyntaxError):
                pass

        raise ValueError(f"Could not parse JSON from response: {text[:200]}")
