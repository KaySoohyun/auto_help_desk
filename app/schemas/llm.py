from pydantic import BaseModel


class LLMPingInfo(BaseModel):
    ok: bool
    model: str
    trace_id: str | None = None