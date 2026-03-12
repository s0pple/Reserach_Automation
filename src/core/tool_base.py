from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field

class ToolArguments(BaseModel):
    """Base class for tool arguments."""
    pass

class BaseTool(ABC):
    """
    Abstract base class for all tools in the Research Automation system.
    Each tool must define its argument schema and an execute method.
    """
    name: str
    description: str
    args_schema: Type[ToolArguments]

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    async def execute(self, args: ToolArguments) -> Any:
        """
        Executes the tool with the given arguments.
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Returns the JSON schema of the tool's arguments.
        """
        return self.args_schema.model_json_schema()
