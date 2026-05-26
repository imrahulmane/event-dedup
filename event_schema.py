from datetime import datetime
from pydantic.config import ConfigDict
from pydantic.main import BaseModel
from pydantic.fields import Field
import time

from typing_extensions import Generic, List, TypeVar

class EventCreate(BaseModel):
    source: str
    event_type: str
    entity_id: str
    timestamp: datetime 
    payload: dict

class EventResponse(BaseModel):
    source: str
    event_type: str
    entity_id: str
    id: int
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)

T = TypeVar("T")
class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    items: List[T]