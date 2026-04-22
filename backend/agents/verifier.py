"""
Verifier Agent - Validate hping3 command against intent using LangChain
"""

from langchain.prompts import PromptTemplate
from langchain.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Optional


class VerificationResult(BaseModel):
    rate_check: Literal["PASS", "FAIL", "WARNING"] = Field(description="rate verification")
    protocol_check: Literal["PASS", "FAIL", "WARNING"] = Field(description="protocol verification")
    stealth_check: Literal["PASS", "FAIL", "WARNING"] = Field(description="stealth verification")
    flag_check: Literal["PASS", "FAIL", "WARNING"] = Field(description="TCP flags verification")
    conflicts: list[str] = Field(default_factory=list, description="detected conflicts")
    final_verdict: Literal["VALID", "INVALID"] = Field(description="overall verdict")
    fix_suggestion: Optional[str] = Field(default=None, description="suggestions to fix issues")


VERIFIER_PROMPT = PromptTemplate(
    template="""You are a Network Test Verifier. Check if generated hping3 command satisfies the test intent.

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
}}

{format_instructions}""",
    input_variables=["nl_input", "dsl_json", "command"],
    partial_variables={"format_instructions": JsonOutputParser().get_format_instructions()}
)


class VerifierAgent:
    def __init__(self, llm):
        self.llm = llm
        self.parser = JsonOutputParser(pydantic_object=VerificationResult)
        self.chain = VERIFIER_PROMPT | self.llm | self.parser

    def verify(self, nl_input: str, dsl: dict, command: str) -> dict:
        """Verify command matches intent"""
        result = self.chain.invoke({
            "nl_input": nl_input,
            "dsl_json": str(dsl),
            "command": command
        })

        if isinstance(result, dict) and "conflicts" not in result:
            result["conflicts"] = []

        if isinstance(result, dict) and "fix_suggestion" not in result:
            result["fix_suggestion"] = None

        return result
