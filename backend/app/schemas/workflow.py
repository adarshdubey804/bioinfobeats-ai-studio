from pydantic import BaseModel, Field
from typing import Any
class WorkflowCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    config: dict[str, Any] = Field(default_factory=dict)
