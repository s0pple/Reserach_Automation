from pydantic import BaseModel, Field
from typing import Optional, Literal

class ResearchParams(BaseModel):
    topic: str = Field(..., description="The topic to research deeply.")

class CLIParams(BaseModel):
    command: str = Field(..., description="The shell command to execute.")

class ProjectParams(BaseModel):
    query: Optional[str] = Field(None, description="Specific query about project status.")

class WatchParams(BaseModel):
    job_id: Optional[str] = Field(None, description="The job ID to watch (display screenshot).")

class GeneralAgentParams(BaseModel):
    goal: str = Field(..., description="A high-level task for the autonomous web agent (e.g., 'Find the cheapest bananas at Migros').")

class SessionParams(BaseModel):
    action: Literal['start', 'input', "read", "kill"] = Field(..., description="The action to perform on the CLI session.")
    session_id: Optional[str] = Field(None, description="A unique identifier for the session (required for input, read, kill).")
    command: Optional[str] = Field(None, description="The command to start the interactive session (e.g., 'npm run start'). Required if action is 'start'.")
    input_text: Optional[str] = Field(None, description="The text/keystrokes to send to the running session. Required if action is 'input'.")
