from typing import Dict, Type, Any, Callable, List, Optional
from pydantic import BaseModel

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable

class ToolRegistry:
    """
    Central registry for all tools. 
    Allows tools to be registered and retrieved by name.
    """
    _tools: Dict[str, ToolInfo] = {}

    @classmethod
    def register_tool(cls, name: str, description: str, func: Callable, schema: Type[BaseModel]):
        """
        Registers a tool for use by the agents.
        
        Args:
            name: Unique identifier for the tool.
            description: Natural language description for the LLM.
            func: The asynchronous function to execute.
            schema: The Pydantic model defining the arguments.
        """
        cls._tools[name] = ToolInfo(
            name=name,
            description=description,
            parameters=schema.model_json_schema(),
            func=func
        )
        print(f"🛠️ Registered Tool: {name}")

    @classmethod
    def get_tool(cls, name: str) -> Optional[ToolInfo]:
        """Retrieves a tool info by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[str]:
        """Lists all registered tool names."""
        return list(cls._tools.keys())

    @classmethod
    def get_all_tools(cls) -> List[ToolInfo]:
        """Returns all registered tools."""
        return list(cls._tools.values())
