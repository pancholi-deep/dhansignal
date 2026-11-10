from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MarketCandle(Base):
    __tablename__ = "market_candles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
