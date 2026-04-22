"""
Orchestrator Agent - Coordinates Planner, Compiler, Verifier using LangChain with Minimax
"""

import os
from dotenv import load_dotenv

load_dotenv()


class MinimaxChatModel:
    """Minimax Chat Model wrapper compatible with LangChain"""

    def __init__(self, api_key: str, model: str = "Minimax-Text-01", base_url: str = "https://api.minimax.chat/v"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/text/chatcompletion_v2"

    def __call__(self, messages: list) -> str:
        """Call Minimax API"""
        import json
        import urllib.request

        payload = {
            "model": self.model,
            "messages": messages
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]


class OrchestratorAgent:
    def __init__(self):
        api_key = os.environ.get("MINIMAX_API_KEY")
        model = os.environ.get("MINIMAX_MODEL", "Minimax-Text-01")

        if not api_key:
            raise ValueError("MINIMAX_API_KEY not found in environment")

        self.llm = MinimaxChatModel(api_key=api_key, model=model)

        from backend.agents.planner import PlannerAgent
        from backend.agents.compiler import CompilerAgent
        from backend.agents.verifier import VerifierAgent

        self.planner = PlannerAgent(self.llm)
        self.compiler = CompilerAgent(self.llm)
        self.verifier = VerifierAgent(self.llm)

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
