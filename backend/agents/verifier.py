"""
Verifier Agent - Validate hping3 command against intent using Minimax
"""

import json
import re


VERIFIER_PROMPT = """You are a Network Test Verifier. Check if generated hping3 command satisfies the test intent.

ORIGINAL INTENT:
{nl_input}

DSL:
{dsl_json}

GENERATED COMMAND:
```bash
{command}
```

CHECKS to perform:
1. RATE: Does command use appropriate rate (-i, --fast, --flood)?
2. PROTOCOL: Does command use correct protocol flag (-1, -2, or none for TCP)?
3. STEALTH: If stealth=true, is --rand-source or spoof present? Is rate low?
4. FLAGS: If tcp_flags specified, are they in command (-S, -A, -F, etc)?
5. PORT: If dest port specified, is -p present?
6. TARGET: Is target hostname/IP present?

Return ONLY valid JSON:
{{
  "rate_check": "PASS | FAIL | WARNING",
  "protocol_check": "PASS | FAIL | WARNING",
  "stealth_check": "PASS | FAIL | WARNING",
  "flag_check": "PASS | FAIL | WARNING",
  "conflicts": ["list of issues found"],
  "final_verdict": "VALID | INVALID",
  "fix_suggestion": "how to fix if INVALID, null otherwise"
}}"""


class VerifierAgent:
    def __init__(self, llm):
        self.llm = llm

    def verify(self, nl_input: str, dsl: dict, command: str) -> dict:
        """Verify command matches intent"""
        prompt = VERIFIER_PROMPT.format(
            nl_input=nl_input,
            dsl_json=str(dsl),
            command=command
        )

        response = self.llm([{"role": "user", "content": prompt}])

        # Extract JSON from response
        result = self._extract_json(response)

        if isinstance(result, dict) and "conflicts" not in result:
            result["conflicts"] = []

        if isinstance(result, dict) and "fix_suggestion" not in result:
            result["fix_suggestion"] = None

        return result

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from response text"""
        # Try to find JSON block
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group(0))

        # Try parsing directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try finding content between braces
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])

        raise ValueError(f"Could not extract JSON from response: {text[:200]}")
