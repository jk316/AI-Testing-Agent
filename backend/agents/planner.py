"""
Planner Agent - NL to DSL using LangChain
"""

from langchain.prompts import PromptTemplate
from langchain.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Literal, Optional


class Intent(BaseModel):
    stealth: bool = Field(default=False, description="stealth mode - low rate, random source")
    scan: bool = Field(default=False, description="port scanning")
    stress: bool = Field(default=False, description="stress/flood testing")
    firewall_test: bool = Field(default=False, description="firewall rule testing")
    performance: bool = Field(default=False, description="performance measurement")
    traceroute: bool = Field(default=False, description="traceroute")
    fingerprint: bool = Field(default=False, description="OS fingerprinting")


class Traffic(BaseModel):
    rate: Literal["low", "medium", "high", "flood"] = Field(default="low", description="traffic rate")
    count: Optional[int] = Field(default=None, description="packet count")
    interval: Optional[str] = Field(default=None, description="interval like u100, u1000")


class Ports(BaseModel):
    source: Optional[str] = Field(default=None, description="source port or 'random'")
    dest: Optional[int] = Field(default=None, description="destination port")


class IPControl(BaseModel):
    ttl: Optional[int] = Field(default=None, description="TTL value")
    spoof: Optional[str] = Field(default=None, description="spoofed IP or 'random'")
    random_source: bool = Field(default=False, description="use random source IP")
    fragment: bool = Field(default=False, description="enable fragmentation")


class Protocol(BaseModel):
    type: Literal["TCP", "UDP", "ICMP"] = Field(default="TCP", description="protocol type")
    tcp_flags: list[str] = Field(default_factory=list, description="TCP flags: SYN, ACK, FIN, RST, PSH, URG")


class DSLOutput(BaseModel):
    target: str = Field(description="target hostname or IP")
    mode: str = Field(default="TCP", description="TCP, UDP, ICMP")
    protocol: Protocol = Field(default_factory=Protocol)
    traffic: Traffic = Field(default_factory=Traffic)
    ports: Ports = Field(default_factory=Ports)
    ip: IPControl = Field(default_factory=IPControl)
    intent: Intent = Field(default_factory=Intent)
    assumptions: list[str] = Field(default_factory=list, description="inferred assumptions")


PLANNER_PROMPT = PromptTemplate(
    template="""You are a Network Test Planner. Convert natural language test intent to structured DSL.

RULES:
- Extract target host/IP from the input
- Infer reasonable defaults for unspecified parameters
- Set stealth=true if user mentions stealth, quiet, silent, covert, or low rate
- Set scan=true if user mentions scan, port discovery
- Set stress=true if user mentions flood, ddos, stress, overwhelm
- Default port is 80 if scanning but not specified
- Default protocol is TCP if not specified

INPUT: {nl_input}

Return ONLY valid JSON matching this schema:
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
}}

{format_instructions}""",
    input_variables=["nl_input"],
    partial_variables={"format_instructions": JsonOutputParser().get_format_instructions()}
)


class PlannerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.chain = PLANNER_PROMPT | self.llm | JsonOutputParser()

    def parse(self, nl_input: str) -> dict:
        """Parse natural language to DSL"""
        result = self.chain.invoke({"nl_input": nl_input})

        if isinstance(result, dict) and "assumptions" not in result:
            result["assumptions"] = []

        if isinstance(result, dict) and "protocol" in result:
            if isinstance(result["protocol"], dict) and "tcp_flags" not in result["protocol"]:
                result["protocol"]["tcp_flags"] = []

        return result
