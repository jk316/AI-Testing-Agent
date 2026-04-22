"""
Orchestrator Agent - Coordinates Planner, Compiler, Verifier using LangChain
"""

from langchain_openai import ChatOpenAI
import os


class OrchestratorAgent:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")

        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=model,
            temperature=0
        )

        from backend.agents.planner import PlannerAgent
        from backend.agents.compiler import CompilerAgent
        from backend.agents.verifier import VerifierAgent

        self.planner = PlannerAgent(self.llm)
        self.compiler = CompilerAgent(self.llm)
        self.verifier = VerifierAgent(self.llm)
        self.max_retries = 2

    def execute(self, nl_input: str) -> dict:
        """Execute the full workflow: Plan -> Compile -> Verify"""
        result = {
            "input": nl_input,
            "status": "success",
            "planner": {"status": "pending", "output": None, "assumptions": []},
            "compiler": {"status": "pending", "output": None, "conflicts": []},
            "verifier": {"status": "pending", "result": None},
            "final_script": None,
            "errors": [],
        }

        # Step 1: Planner
        try:
            result["planner"]["status"] = "running"
            dsl = self.planner.parse(nl_input)
            result["planner"] = {
                "status": "success",
                "output": dsl,
                "assumptions": dsl.get("assumptions", []),
            }
        except Exception as e:
            result["planner"]["status"] = "error"
            result["status"] = "error"
            result["errors"].append(f"Planner error: {str(e)}")
            return result

        # Step 2: Compiler
        try:
            result["compiler"]["status"] = "running"
            script, conflicts = self.compiler.compile(dsl)
            result["compiler"] = {
                "status": "success",
                "output": script,
                "conflicts": conflicts,
            }
        except Exception as e:
            result["compiler"]["status"] = "error"
            result["status"] = "error"
            result["errors"].append(f"Compiler error: {str(e)}")
            return result

        # Step 3: Verifier
        try:
            result["verifier"]["status"] = "running"
            verification = self.verifier.verify(nl_input, dsl, script)
            result["verifier"] = {
                "status": "success",
                "result": verification,
            }

            if verification.get("final_verdict") == "INVALID":
                result["status"] = "invalid"

        except Exception as e:
            result["verifier"]["status"] = "error"
            result["verifier"]["error"] = str(e)
            result["errors"].append(f"Verifier error: {str(e)}")

        result["final_script"] = result["compiler"]["output"]
        return result

    def get_status_steps(self) -> list[dict]:
        """Return workflow steps for status display"""
        return [
            {"id": "planner", "name": "Planner Agent", "description": "NL → DSL"},
            {"id": "compiler", "name": "Compiler Agent", "description": "DSL → hping3"},
            {"id": "verifier", "name": "Verifier Agent", "description": "Semantic Validation"},
        ]
