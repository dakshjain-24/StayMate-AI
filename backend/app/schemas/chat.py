from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str = "demo-thread"
    hotel_id: int = 1


class ChatResponse(BaseModel):
    answer: str
    thread_id: str
