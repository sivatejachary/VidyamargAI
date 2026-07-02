from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolDefinitionSchema(BaseModel):
    name: str = Field(..., description="Unique tool capability string")
    description: str = Field(..., description="Detailed description of tool functionality for model selection")
    input_schema: Dict[str, Any] = Field(..., description="Pydantic/JSON model schema of inputs")
    permission_required: str = Field(..., description="Required ABAC authorization tag")
    timeout: float = Field(default=30.0, description="Execution timeout limit in seconds")

class ToolCallPayload(BaseModel):
    call_id: str = Field(..., description="Unique correlation execution ID")
    name: str = Field(..., description="Target tool name to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Key-value arguments for tool parameters")

class ToolResultPayload(BaseModel):
    call_id: str = Field(..., description="Correlation execution ID mapping back to Call")
    success: bool = Field(..., description="Indicates if tool completed successfully")
    result: Optional[Any] = Field(default=None, description="Output payload result of the tool action")
    error: Optional[str] = Field(default=None, description="System error code details if success is False")
    latency_ms: float = Field(default=0.0, description="Total execution latency in milliseconds")
