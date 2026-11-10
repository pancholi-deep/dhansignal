import json
import re
from pathlib import Path
from datetime import timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import PaperAccount, PaperPosition, PaperTrade, ResearchChunk, ResearchDocument, WatchlistItem
from app.core.config import settings
from app.market_data.factory import get_market_data_provider
from app.market_data.demo import DEFAULT_SYMBOLS
from app.services.market import get_signals
from app.strategies.technical import add_indicators
from app.services.research import MAX_PDF_BYTES, ResearchFileError, chunk_pdf, inspect_pdf, save_pdf, rank_chunks

router = APIRouter()
PAPER_FEE_RATE = 0.001  # 0.10% simulated fee per side


class PaperOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9&_-]+$")
    side: str = Field(pattern=r"^(BUY|SELL)$")
    quantity: int = Field(gt=0, le=10000)


def get_or_create_paper_account(db: Session) -> PaperAccount:
    account = db.query(PaperAccount).order_by(PaperAccount.id).with_for_update().first()
    if account is None:
        account = PaperAccount(name="Default paper account", starting_cash=settings.paper_starting_cash, cash_balance=settings.paper_starting_cash)
        db.add(account)
        db.flush()
    return account


def paper_snapshot(db: Session, account: PaperAccount):
    market = get_market_data_provider()
    positions = db.query(PaperPosition).filter(PaperPosition.account_id == account.id, PaperPosition.quantity > 0).order_by(PaperPosition.symbol).all()
    quotes = {q["symbol"]: q for q in market.get_quotes([p.symbol for p in positions])} if positions else {}
    position_rows = []
    invested_value = unrealized_pnl = 0.0
    for position in positions:
        quote = quotes.get(position.symbol, {})
        ltp = float(quote.get("last_price") or position.average_price)
        market_value = ltp * position.quantity
        cost_value = position.average_price * position.quantity
        pnl = market_value - cost_value
        invested_value += market_value
        unrealized_pnl += pnl
        position_rows.append({
            "symbol": position.symbol, "quantity": position.quantity,
            "average_price": round(position.average_price, 2), "last_price": round(ltp, 2),
            "market_value": round(market_value, 2), "unrealized_pnl": round(pnl, 2),
            "realized_pnl": round(position.realized_pnl, 2),
        })
    realized_pnl = sum(p.realized_pnl for p in db.query(PaperPosition).filter(PaperPosition.account_id == account.id).all())
    return {
        "id": account.id, "currency": "INR", "starting_cash": round(account.starting_cash, 2),
        "cash_balance": round(account.cash_balance, 2), "invested_value": round(invested_value, 2),
        "total_value": round(account.cash_balance + invested_value, 2),
        "realized_pnl": round(realized_pnl, 2), "unrealized_pnl": round(unrealized_pnl, 2),
        "positions": position_rows, "mode": "PAPER", "provider": market.name,
    }


@router.get("/market/overview")
def market_overview():
    market = get_market_data_provider()
    return {"provider": market.name, "is_live": market.is_live, "indices": market.get_indices()}


@router.get("/market/watchlist")
def watchlist():
    market = get_market_data_provider()
    db: Session = SessionLocal()
    try:
        symbols = [row.symbol for row in db.query(WatchlistItem).order_by(WatchlistItem.id).all()] or DEFAULT_SYMBOLS
    finally:
        db.close()
    return {"symbols": symbols, "quotes": market.get_quotes(symbols), "provider": market.name, "is_live": market.is_live}


@router.get("/market/quotes")
def quotes(symbols: str = Query(..., description="Comma-separated NSE symbols")):
    requested = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    if not requested or len(requested) > 50:
        raise HTTPException(status_code=400, detail="Provide between 1 and 50 symbols")
    market = get_market_data_provider()
    return {"quotes": market.get_quotes(requested), "provider": market.name, "is_live": market.is_live}


@router.get("/market/history/{symbol}")
def history(symbol: str, interval: str = "day", days: int = Query(365, ge=30, le=2000)):
    if interval not in {"minute", "5minute", "15minute", "30minute", "60minute", "day"}:
        raise HTTPException(status_code=400, detail="Unsupported candle interval")
    market = get_market_data_provider()
    frame = market.get_history(symbol.upper(), interval=interval, days=days)
    if frame.empty:
        raise HTTPException(status_code=404, detail="No historical data found")
    frame = add_indicators(frame)
    frame["date"] = frame["date"].map(lambda value: value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)[:10])
    candles = json.loads(frame.to_json(orient="records"))
    return {"symbol": symbol.upper(), "provider": market.name, "is_live": market.is_live, "candles": candles}


@router.get("/signals")
def signals(symbols: str = ",".join(DEFAULT_SYMBOLS)):
    requested = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    if not requested or len(requested) > 30:
        raise HTTPException(status_code=400, detail="Provide between 1 and 30 symbols")
    return {"signals": get_signals(requested), "provider": get_market_data_provider().name}


@router.get("/paper/account")
def paper_account():
    db: Session = SessionLocal()
    try:
        account = get_or_create_paper_account(db)
        db.commit()
        return paper_snapshot(db, account)
    finally:
        db.close()


@router.post("/paper/orders")
def place_paper_order(order: PaperOrderRequest):
    symbol, side = order.symbol.upper(), order.side.upper()
    db: Session = SessionLocal()
    try:
        account = get_or_create_paper_account(db)
        market = get_market_data_provider()
        quote_rows = market.get_quotes([symbol])
        quote = next((q for q in quote_rows if q.get("symbol") == symbol), None)
        if not quote or not quote.get("last_price") or float(quote["last_price"]) <= 0:
            raise HTTPException(status_code=404, detail=f"No usable quote found for {symbol}")
        price = float(quote["last_price"])
        notional = price * order.quantity
        fees = round(notional * PAPER_FEE_RATE, 2)
        position = db.query(PaperPosition).filter_by(account_id=account.id, symbol=symbol).with_for_update().first()

        if side == "BUY":
            total_cost = notional + fees
            if total_cost > account.cash_balance:
                raise HTTPException(status_code=400, detail="Insufficient paper cash for this order, including simulated fees")
            if position is None:
                position = PaperPosition(account_id=account.id, symbol=symbol, quantity=0, average_price=0, realized_pnl=0)
                db.add(position)
                db.flush()
            new_quantity = position.quantity + order.quantity
            position.average_price = ((position.quantity * position.average_price) + notional + fees) / new_quantity
            position.quantity = new_quantity
            account.cash_balance -= total_cost
            realized = 0.0
        else:
            if position is None or position.quantity < order.quantity:
                available = position.quantity if position else 0
                raise HTTPException(status_code=400, detail=f"Insufficient shares to sell. Available: {available}")
            proceeds = notional - fees
            realized = (price - position.average_price) * order.quantity - fees
            position.quantity -= order.quantity
            position.realized_pnl += realized
            account.cash_balance += proceeds
            if position.quantity == 0:
                position.average_price = 0.0

        trade = PaperTrade(account_id=account.id, symbol=symbol, side=side, quantity=order.quantity, price=price, fees=fees, realized_pnl=realized)
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return {
            "message": f"Paper {side.lower()} order filled",
            "trade": {"id": trade.id, "symbol": symbol, "side": side, "quantity": order.quantity,
                      "price": round(price, 2), "fees": fees, "realized_pnl": round(realized, 2),
                      "created_at": trade.created_at.isoformat() if trade.created_at else None},
            "account": paper_snapshot(db, account),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/paper/trades")
def paper_trades(limit: int = Query(50, ge=1, le=200)):
    db: Session = SessionLocal()
    try:
        account = get_or_create_paper_account(db)
        db.commit()
        trades = db.query(PaperTrade).filter(PaperTrade.account_id == account.id).order_by(PaperTrade.id.desc()).limit(limit).all()
        return {"trades": [{
            "id": t.id, "symbol": t.symbol, "side": t.side, "quantity": t.quantity,
            "price": round(t.price, 2), "fees": round(t.fees, 2),
            "realized_pnl": round(t.realized_pnl, 2),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in trades]}
    finally:
        db.close()


RESEARCH_TYPES = {
    "annual_report", "management_discussion", "earnings_transcript",
    "technical_chart", "financial_screener", "shareholding_pattern",
}


def research_document_payload(document: ResearchDocument, include_text: bool = False):
    payload = {
        "id": document.id, "title": document.title,
        "original_filename": document.original_filename,
        "document_type": document.document_type,
        "company_name": document.company_name, "symbol": document.symbol,
        "reporting_period": document.reporting_period,
        "file_size": document.file_size, "page_count": document.page_count,
        "status": document.status,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "text_length": len(document.extracted_text or ""),
    }
    if include_text:
        payload["extracted_text"] = document.extracted_text
    return payload


@router.post("/research/documents")
async def upload_research_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    company_name: str = Form(...),
    title: str | None = Form(None),
    symbol: str | None = Form(None),
    reporting_period: str | None = Form(None),
):
    document_type = document_type.strip().lower()
    company_name = company_name.strip()
    if document_type not in RESEARCH_TYPES:
        raise HTTPException(status_code=400, detail=f"document_type must be one of: {', '.join(sorted(RESEARCH_TYPES))}")
    if not company_name or len(company_name) > 160:
        raise HTTPException(status_code=400, detail="company_name is required and must be at most 160 characters")
    if symbol and len(symbol.strip()) > 32:
        raise HTTPException(status_code=400, detail="symbol must be at most 32 characters")
    if reporting_period and len(reporting_period.strip()) > 80:
        raise HTTPException(status_code=400, detail="reporting_period must be at most 80 characters")
    if title and len(title.strip()) > 240:
        raise HTTPException(status_code=400, detail="title must be at most 240 characters")
    content = await file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the 20 MB upload limit")
    try:
        extracted_text, page_count, digest = inspect_pdf(content)
    except ResearchFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db: Session = SessionLocal()
    try:
        existing = db.query(ResearchDocument).filter_by(sha256=digest).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"This PDF is already uploaded as document #{existing.id}")
        safe_name = Path(file.filename or "research.pdf").name[:255]
        title_value = (title or "").strip() or safe_name.rsplit(".", 1)[0]
        storage_path = save_pdf(content, digest)
        doc = ResearchDocument(
            title=title_value[:240],
            original_filename=safe_name, document_type=document_type,
            company_name=company_name, symbol=(symbol or "").strip().upper() or None,
            reporting_period=(reporting_period or "").strip() or None,
            storage_path=storage_path, mime_type="application/pdf",
            file_size=len(content), sha256=digest, page_count=page_count,
            extracted_text=extracted_text, status="processed",
        )
        db.add(doc)
        db.flush()
        chunks = chunk_pdf(content)
        db.add_all([ResearchChunk(document_id=doc.id, **chunk) for chunk in chunks])
        db.commit()
        db.refresh(doc)
        return {**research_document_payload(doc), "chunk_count": len(chunks)}
    finally:
        db.close()


@router.get("/research/documents")
def list_research_documents(
    document_type: str | None = None,
    symbol: str | None = None,
    limit: int = Query(100, ge=1, le=200),
):
    db: Session = SessionLocal()
    try:
        query = db.query(ResearchDocument)
        if document_type:
            if document_type not in RESEARCH_TYPES:
                raise HTTPException(status_code=400, detail="Unsupported document_type")
            query = query.filter(ResearchDocument.document_type == document_type)
        if symbol:
            query = query.filter(ResearchDocument.symbol == symbol.strip().upper())
        documents = query.order_by(ResearchDocument.created_at.desc()).limit(limit).all()
        return {"documents": [research_document_payload(doc) for doc in documents], "count": len(documents)}
    finally:
        db.close()


@router.get("/research/documents/{document_id}")
def get_research_document(document_id: int):
    db: Session = SessionLocal()
    try:
        doc = db.query(ResearchDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Research document not found")
        return research_document_payload(doc, include_text=True)
    finally:
        db.close()


@router.get("/research/search")
def search_research_documents(q: str = Query(..., min_length=2, max_length=200), symbol: str | None = None, limit: int = Query(20, ge=1, le=100)):
    term = q.strip()
    db: Session = SessionLocal()
    try:
        query = db.query(ResearchDocument).filter(ResearchDocument.extracted_text.ilike(f"%{term}%"))
        if symbol:
            query = query.filter(ResearchDocument.symbol == symbol.strip().upper())
        docs = query.order_by(ResearchDocument.created_at.desc()).limit(limit).all()
        snippets = []
        for doc in docs:
            text_value = doc.extracted_text or ""
            match = re.search(re.escape(term), text_value, re.IGNORECASE)
            start = max(0, match.start() - 180) if match else 0
            end = min(len(text_value), (match.end() + 220) if match else 400)
            snippets.append({
                **research_document_payload(doc),
                "snippet": text_value[start:end].replace("\n", " "),
            })
        return {"query": term, "results": snippets, "count": len(snippets)}
    finally:
        db.close()



@router.post("/research/documents/{document_id}/index")
def index_research_document(document_id: int):
    """Create page-aware chunks for a previously uploaded document."""
    db: Session = SessionLocal()
    try:
        doc = db.query(ResearchDocument).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Research document not found")
        if db.query(ResearchChunk).filter_by(document_id=doc.id).count():
            return {"document_id": doc.id, "message": "Document is already indexed"}
        try:
            content = Path(doc.storage_path).read_bytes()
            chunks = chunk_pdf(content)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not index stored PDF: {exc}") from exc
        db.add_all([ResearchChunk(document_id=doc.id, **chunk) for chunk in chunks])
        db.commit()
        return {"document_id": doc.id, "chunk_count": len(chunks), "message": "Document indexed"}
    finally:
        db.close()


@router.get("/research/retrieve")
def retrieve_research_evidence(
    q: str = Query(..., min_length=2, max_length=300),
    symbol: str | None = None,
    document_type: str | None = None,
    limit: int = Query(8, ge=1, le=30),
):
    """Return ranked, page-cited evidence passages for analyst workflows."""
    terms = re.findall(r"[a-zA-Z0-9₹]+", q.lower())
    if not any(len(term) > 1 for term in terms):
        raise HTTPException(status_code=400, detail="Query must contain searchable terms")
    db: Session = SessionLocal()
    try:
        query = db.query(ResearchChunk, ResearchDocument).join(
            ResearchDocument, ResearchChunk.document_id == ResearchDocument.id
        )
        if symbol:
            query = query.filter(ResearchDocument.symbol == symbol.strip().upper())
        if document_type:
            if document_type not in RESEARCH_TYPES:
                raise HTTPException(status_code=400, detail="Unsupported document_type")
            query = query.filter(ResearchDocument.document_type == document_type)
        rows = query.limit(5000).all()
        candidates = []
        for chunk, doc in rows:
            candidates.append({
                "id": chunk.id, "document_id": doc.id, "title": doc.title,
                "company_name": doc.company_name, "symbol": doc.symbol,
                "document_type": doc.document_type, "reporting_period": doc.reporting_period,
                "page_number": chunk.page_number, "chunk_index": chunk.chunk_index,
                "content": chunk.content,
            })
        ranked = rank_chunks(candidates, q)[:limit]
        return {"query": q, "results": ranked, "count": len(ranked), "retrieval": "lexical-v1"}
    finally:
        db.close()
