from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class AgentSpec:
    key: str
    name: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
class BaseAgent:
    spec: AgentSpec
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
