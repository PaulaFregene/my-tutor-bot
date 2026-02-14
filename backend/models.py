# Pydantic request/response models

# from typing import Optional
from pydantic import BaseModel

class QueryRequest(BaseModel):
    question: str
    mode: str
    anon_user_id: str

class HistoryRequest(BaseModel):
    anon_user_id: str
