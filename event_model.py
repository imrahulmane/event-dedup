from datetime import datetime
import json
from annotated_types import Timezone
from pydantic.main import BaseModel
from pydantic.fields import Field
import time
from pydantic.types import Json
from sqlalchemy import Column, String
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm.base import Mapped
from sqlalchemy.orm.decl_api import DeclarativeBase
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.schema import Index, UniqueConstraint
from sqlalchemy.sql.sqltypes import DateTime
from typing_extensions import Any, Dict
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    pass

class EventModel(Base):
    __tablename__ = 'events'

    id : Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30))
    event_type: Mapped[str] = mapped_column(String(255))
    entity_id: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, server_default='{}') 
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        Index(
            "ix_source_evnt_type_entity_id",
            "source",
            "event_type",
            "entity_id"
        ),
        UniqueConstraint(
            "source",
            "event_type",
            "entity_id",
            name="uq_source_evnt_typ_entity_id"
        ),
    )