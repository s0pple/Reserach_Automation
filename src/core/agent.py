from abc import ABC, abstractmethod
from typing import Optional
from src.schema.research_state import ResearchState
from src.core.llm import LLMClient

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """
    def __init__(self, name: str, llm: Optional[LLMClient] = None):
        self.name = name
        self.llm = llm

    @abstractmethod
    async def process(self, state: ResearchState) -> ResearchState:
        pass

    def __repr__(self):
        return f"<Agent: {self.name}>"
