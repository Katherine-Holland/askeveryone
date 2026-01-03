from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=6000)
    session_id: Optional[str] = None
    compare: book = False
    mode: str = "text"  # "text" or "voice" (future)

class AskResponse(BaseModel):
    query_id: str
    answer: str
    intent: str
    provider_used: str
    providers_called: List[str]
    confidence: float
    multi_call: bool
    meta: Dict[str, Any] = {}
