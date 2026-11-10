from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.db.session import Base, engine, SessionLocal
from app.db import models  # noqa: F401
from app.db.models import PaperAccount, WatchlistItem
from app.api.routes import router
from app.services.stream import market_stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    market_stream.start()
    db = SessionLocal()
    try:
        if db.query(PaperAccount).count() == 0:
            db.add(PaperAccount(name="Default paper account", starting_cash=settings.paper_starting_cash, cash_balance=settings.paper_starting_cash))
        if db.query(WatchlistItem).count() == 0:
            for symbol in ["RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "TCS", "LT"]:
                db.add(WatchlistItem(symbol=symbol, exchange="NSE"))
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        database = "unavailable"
    return {"status": "ok", "database": database, "environment": settings.app_env}
