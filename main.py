import uuid
from fastapi.exceptions import HTTPException
from fastapi.param_functions import Query
from redis.exceptions import RedisError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.sql.functions import func
from starlette import status
from starlette.responses import JSONResponse
from event_model import Base, EventModel
from event_schema import EventCreate, EventResponse, PaginatedResponse
import logging
from metrics import (
    metrics_app,
    events_received_total,
    accepted_events_total,
    event_processing_seconds,
    duplicate_events_received_total
)
from settings import settings

engine = create_async_engine(
    url=settings.DATABASE_URL, 
    echo=False,
    pool_size=10,
    max_overflow=15,
    pool_timeout=30
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

RELEASE_LOCK_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0    
    end
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.release_lock = app.state.redis.register_script(RELEASE_LOCK_SCRIPT)
    yield

    await app.state.redis.aclose()
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.mount("/metrics", metrics_app)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


@app.get("/health")
async def health():
    db_status = "down"
    try:
        async with SessionLocal() as db:
            result = await db.execute(text("SELECT 1"))
            if result.scalar() == 1:
                db_status = "ok"
    except OperationalError:
        pass

    redis_status = "down"
    try:
        await app.state.redis.ping()
        redis_status= "ok"
    except RedisError:
        pass

    body = {
        "db" : db_status, "redis" : redis_status
    }
    
    if db_status != "ok" or redis_status != "ok":
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=body
        )
        
    return body
    
@app.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def consume_events(data : EventCreate):
    with event_processing_seconds.time():
        composite_key: str = data.source + ":" + data.event_type + ":" + data.entity_id
        lock_value = str(uuid.uuid4())
        events_received_total.inc()
        redis_locked=False
        
        try:
            ok = await app.state.redis.set(composite_key, lock_value, nx=True, ex=settings.DEDUP_TTL_SECONDS)
            if not ok:
                duplicate_events_received_total.inc()
                
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT, 
                    content="Key already present"
                )
                
            redis_locked=True
                
        except RedisError:
            if settings.DEDUP_STRICT_MODE:
                logger.error("Redis down!!")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Redis is down!!"
                )
                
            logger.warning("Redis unavailable, accepting event without dedup")
        
        db_event = EventModel(
            source = data.source,
            event_type = data.event_type,
            entity_id = data.entity_id,
            timestamp = data.timestamp,
            payload = data.payload
        )
    
        async with SessionLocal() as session:
            try:
                session.add(db_event)
                await session.commit()
                await session.refresh(db_event)
                accepted_events_total.inc()
                return db_event
                
            except OperationalError:
                await session.rollback()

                if redis_locked:
                    try:
                        await app.state.release_lock(keys=[composite_key], args=[lock_value])
                    except RedisError:
                        logger.exception("Failed to release lock -- Redis also down!!")
                        
                logger.error("Database is down!!")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database connection failed!"
                )
                
            except IntegrityError:
                await session.rollback()
               
                if redis_locked:
                    try:
                        await app.state.release_lock(keys=[composite_key], args=[lock_value])
                    except RedisError:
                        logger.exception("Failed to release lock -- Redis also down!!")
                 
                duplicate_events_received_total.inc()
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content="Duplicate event!!"
                )
    
            except Exception:
                await session.rollback()
 
                if redis_locked:
                    try:
                        await app.state.release_lock(keys=[composite_key], args=[lock_value])
                    except RedisError:
                        logger.exception("Failed to release lock -- Redis also down!!")
 
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected error!!"
                )

@app.get(path="/events", response_model=PaginatedResponse[EventResponse], status_code=status.HTTP_200_OK)
async def get_events(
    page: int = Query(1, ge=1, description="page number"), 
    size: int = Query(50, ge=1, le=100, description="Items per page")
):
    offset = (page-1)*size

    async with SessionLocal() as db:
        count_statement = select(func.count()).select_from(EventModel)
        total_result = await db.execute(count_statement)
        total_count = total_result.scalar_one()

        fetch_statement = (
            select(EventModel)
            .order_by(EventModel.received_at.desc())
            .offset(offset)
            .limit(size)
        )
        
        
        fetch_results = await db.execute(fetch_statement)
        items = fetch_results.scalars().all()

        return PaginatedResponse(
            total=total_count,
            page=page,
            size=size,
            items=items
        )