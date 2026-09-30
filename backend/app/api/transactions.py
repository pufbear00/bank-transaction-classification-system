"""Transactions API: CRUD + filter + export."""
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete, cast, String
import io

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate, TransactionResponse, TransactionListResponse,
    TransactionUpdate, BulkUpdateRequest,
)
from app.services.classification_service import ClassificationService
from app.services.export_service import export_transactions_xlsx

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    entity: Optional[str] = None,
    account: Optional[str] = None,
    ccy: Optional[str] = None,
    management: Optional[str] = None,
    grouping: Optional[str] = None,
    class_name: Optional[str] = None,
    cf_line: Optional[str] = None,
    unclassified: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    sort_by: str = Query("period", regex="^(period|cf|cf_in_cny|entity|account|management|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if entity:
        conditions.append(Transaction.entity == entity)
    if account:
        acct_list = [a.strip() for a in account.split(",") if a.strip()]
        conditions.append(Transaction.account.in_(acct_list) if len(acct_list) > 1 else Transaction.account == acct_list[0])
    if ccy:
        conditions.append(Transaction.ccy == ccy)
    if management:
        conditions.append(Transaction.management == management)
    if grouping:
        conditions.append(Transaction.grouping == grouping)
    if class_name:
        conditions.append(Transaction.class_name == class_name)
    if cf_line:
        conditions.append(Transaction.cf_line == cf_line)
    if unclassified:
        conditions.append(Transaction.management.is_(None))
    if start_date:
        conditions.append(Transaction.period >= start_date)
    if end_date:
        conditions.append(Transaction.period <= end_date)
    if search:
        like = f"%{search}%"
        text_match = or_(
            Transaction.abstract.ilike(like),
            Transaction.counterpart.ilike(like),
        )
        # If search looks numeric, also match cf amount
        search_clean = search.replace(",", "").strip()
        try:
            amount = float(search_clean)
            # Match both positive and negative (e.g. searching "6943" finds cf=6943.13 and cf=-6943.13)
            amount_match = or_(
                cast(Transaction.cf, String).like(f"%{search_clean}%"),
                cast(Transaction.cf_in_cny, String).like(f"%{search_clean}%"),
            )
            conditions.append(or_(text_match, amount_match))
        except ValueError:
            conditions.append(text_match)

    where = and_(*conditions) if conditions else True

    # Count + sums
    stats_q = select(
        func.count(),
        func.coalesce(func.sum(Transaction.cf), 0),
        func.coalesce(func.sum(Transaction.cf_in_cny), 0),
    ).select_from(Transaction).where(where)
    stats_row = (await db.execute(stats_q)).one()
    total, sum_cf, sum_cf_in_cny = int(stats_row[0]), float(stats_row[1]), float(stats_row[2])

    # Sort
    sort_col = getattr(Transaction, sort_by, Transaction.period)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    # Query
    q = (
        select(Transaction)
        .where(where)
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    items = list(result.scalars().all())

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        sum_cf=round(sum_cf, 2),
        sum_cf_in_cny=round(sum_cf_in_cny, 2),
    )


@router.get("/export")
async def export_transactions(
    entity: Optional[str] = None,
    account: Optional[str] = None,
    ccy: Optional[str] = None,
    management: Optional[str] = None,
    grouping: Optional[str] = None,
    class_name: Optional[str] = None,
    cf_line: Optional[str] = None,
    unclassified: Optional[bool] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if entity:
        conditions.append(Transaction.entity == entity)
    if account:
        acct_list = [a.strip() for a in account.split(",") if a.strip()]
        conditions.append(Transaction.account.in_(acct_list) if len(acct_list) > 1 else Transaction.account == acct_list[0])
    if ccy:
        conditions.append(Transaction.ccy == ccy)
    if management:
        conditions.append(Transaction.management == management)
    if grouping:
        conditions.append(Transaction.grouping == grouping)
    if class_name:
        conditions.append(Transaction.class_name == class_name)
    if cf_line:
        conditions.append(Transaction.cf_line == cf_line)
    if unclassified:
        conditions.append(Transaction.management.is_(None))
    if start_date:
        conditions.append(Transaction.period >= start_date)
    if end_date:
        conditions.append(Transaction.period <= end_date)
    if search:
        like = f"%{search}%"
        text_match = or_(
            Transaction.abstract.ilike(like),
            Transaction.counterpart.ilike(like),
        )
        search_clean = search.replace(",", "").strip()
        try:
            float(search_clean)
            amount_match = or_(
                cast(Transaction.cf, String).like(f"%{search_clean}%"),
                cast(Transaction.cf_in_cny, String).like(f"%{search_clean}%"),
            )
            conditions.append(or_(text_match, amount_match))
        except ValueError:
            conditions.append(text_match)

    where = and_(*conditions) if conditions else True
    q = select(Transaction).where(where).order_by(Transaction.period.desc())
    result = await db.execute(q)
    transactions = list(result.scalars().all())

    xlsx_bytes = export_transactions_xlsx(transactions)

    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=transactions.xlsx"},
    )


@router.post("/fix-exchange-rates")
async def fix_exchange_rates(
    force: bool = Query(False, description="强制重算所有非CNY交易的汇率"),
    db: AsyncSession = Depends(get_db),
):
    """Fix non-CNY transactions exchange rates.

    force=False: only fix NULL/1.0 rates (default)
    force=True: recalculate ALL non-CNY transactions
    """
    from app.services.exchange_rate_service import ExchangeRateService
    from app.models.exchange_rate import ExchangeRate

    # When force=True, clear fallback cached rates so API is re-queried
    if force:
        await db.execute(
            delete(ExchangeRate).where(ExchangeRate.source == "fallback")
        )
        await db.flush()

    if force:
        result = await db.execute(
            select(Transaction).where(Transaction.ccy != "CNY")
        )
    else:
        result = await db.execute(
            select(Transaction).where(
                Transaction.ccy != "CNY",
                or_(Transaction.exchange_rate.is_(None), Transaction.exchange_rate == 1.0),
            )
        )
    txns = list(result.scalars().all())
    if not txns:
        return {"total": 0, "fixed": 0}

    fx_svc = ExchangeRateService(db)
    fixed = 0
    for txn in txns:
        rate = await fx_svc.get_rate(txn.period, txn.ccy, "CNY")
        if rate and (force or rate != 1.0):
            old_rate = txn.exchange_rate
            txn.exchange_rate = rate
            txn.cf_in_cny = round(txn.cf * rate, 2)
            if old_rate != rate:
                fixed += 1

    await db.flush()
    return {"total": len(txns), "fixed": fixed}


@router.post("/reclassify")
async def reclassify_unclassified(
    db: AsyncSession = Depends(get_db),
):
    """Re-run classification on all unclassified transactions (management IS NULL)."""
    result = await db.execute(
        select(Transaction).where(Transaction.management.is_(None))
    )
    unclassified = list(result.scalars().all())

    if not unclassified:
        return {"total_unclassified": 0, "classified": 0, "still_unclassified": 0}

    cls_svc = ClassificationService(db)
    classified_count = 0

    for txn in unclassified:
        classification = await cls_svc.classify_transaction(
            abstract=txn.abstract or "",
            counterpart=txn.counterpart,
            amount=txn.cf,
            entity=txn.entity,
        )
        if classification.get("management"):
            txn.management = classification["management"]
            txn.grouping = classification.get("grouping")
            txn.class_name = classification.get("class_name")
            txn.cf_line = classification.get("cf_line")
            txn.classification_method = classification.get("method")
            txn.classification_confidence = classification.get("confidence")
            classified_count += 1

    await db.flush()
    return {
        "total_unclassified": len(unclassified),
        "classified": classified_count,
        "still_unclassified": len(unclassified) - classified_count,
    }


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Manually create a single transaction."""
    from app.services.exchange_rate_service import ExchangeRateService

    row = data.model_dump()

    # Auto-fetch exchange rate for non-CNY currencies
    ccy = row.get("ccy", "CNY")
    if ccy != "CNY" and (row.get("exchange_rate") is None or row.get("exchange_rate") == 1.0):
        fx_svc = ExchangeRateService(db)
        rate = await fx_svc.get_rate(row["period"], ccy, "CNY")
        row["exchange_rate"] = rate

    # Compute cf_in_cny
    rate = row.get("exchange_rate") or 1.0
    row["cf_in_cny"] = row["cf"] * rate

    # If management is set, auto-fill grouping/class/cf_line
    if row.get("management"):
        cls_svc = ClassificationService(db)
        lookup = await cls_svc.lookup_category(row["management"])
        if lookup:
            if not row.get("grouping"):
                row["grouping"] = lookup["grouping"]
            if not row.get("class_name"):
                row["class_name"] = lookup["class_name"]
            if not row.get("cf_line"):
                row["cf_line"] = lookup["cf_line"]
        row.setdefault("classification_method", "manual")

    row["import_batch"] = "manual"

    # Compute dedup_hash
    import hashlib
    parts = [
        row.get("entity", ""),
        row.get("account", ""),
        str(row.get("period", "")),
        str(row.get("cf", "")),
        row.get("abstract", "") or "",
        row.get("counterpart", "") or "",
    ]
    row["dedup_hash"] = hashlib.sha256("|".join(parts).encode()).hexdigest()

    txn = Transaction(**row)
    db.add(txn)
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="重复流水记录")

    return TransactionResponse.model_validate(txn)


@router.put("/{txn_id}", response_model=TransactionResponse)
async def update_transaction(
    txn_id: int,
    data: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transaction).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = data.model_dump(exclude_unset=True)

    # If management is updated, auto-fill grouping/class/cf_line
    if "management" in update_data and update_data["management"]:
        cls_svc = ClassificationService(db)
        lookup = await cls_svc.lookup_category(update_data["management"])
        if lookup:
            update_data.setdefault("grouping", lookup["grouping"])
            update_data.setdefault("class_name", lookup["class_name"])
            update_data.setdefault("cf_line", lookup["cf_line"])
        update_data.setdefault("classification_method", "manual")
        update_data.setdefault("classification_confidence", 1.0)

        # Learn this classification
        keyword = txn.counterpart or txn.abstract
        if keyword and len(keyword) >= 2:
            await cls_svc.add_learned_rule(
                keyword=keyword,
                management=update_data["management"],
                grouping=update_data.get("grouping", ""),
                class_name=update_data.get("class_name", ""),
                cf_line=update_data.get("cf_line"),
            )

    for k, v in update_data.items():
        setattr(txn, k, v)

    # Auto-fix exchange rate for non-CNY transactions missing a rate
    if txn.ccy and txn.ccy != "CNY" and (txn.exchange_rate is None or txn.exchange_rate == 1.0):
        from app.services.exchange_rate_service import ExchangeRateService
        fx_svc = ExchangeRateService(db)
        rate = await fx_svc.get_rate(txn.period, txn.ccy, "CNY")
        txn.exchange_rate = rate
        txn.cf_in_cny = round(txn.cf * rate, 2)

    return TransactionResponse.model_validate(txn)


@router.patch("/bulk", response_model=dict)
async def bulk_update_transactions(
    data: BulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(Transaction.id.in_(data.ids))
    )
    transactions = list(result.scalars().all())

    # 只有真正改了分类字段时才回写分类方法/置信度，
    # 否则纯改账户/实体会误把分类标成 manual。
    cls_changed = any([data.management, data.grouping, data.class_name, data.cf_line])
    # 改了实体/账户要重算去重哈希，否则同一份流水再次导入时查重会失效、造成重复。
    identity_changed = bool(data.entity or data.account)
    if identity_changed:
        from app.services.deduplication_service import compute_dedup_hash

    updated = 0
    for txn in transactions:
        if data.entity:
            txn.entity = data.entity
        if data.account:
            txn.account = data.account
        if data.management:
            txn.management = data.management
        if data.grouping:
            txn.grouping = data.grouping
        if data.class_name:
            txn.class_name = data.class_name
        if data.cf_line:
            txn.cf_line = data.cf_line
        if cls_changed:
            txn.classification_method = data.classification_method
            txn.classification_confidence = 1.0
        if identity_changed:
            txn.dedup_hash = compute_dedup_hash(
                txn.entity, txn.account, txn.period,
                txn.cf, txn.abstract, txn.counterpart,
            )
        updated += 1

    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="改账户后与已有流水重复，存在去重哈希冲突")

    return {"updated": updated}


@router.delete("/bulk")
async def bulk_delete_transactions(
    entity: Optional[str] = None,
    account: Optional[str] = None,
    ccy: Optional[str] = None,
    management: Optional[str] = None,
    grouping: Optional[str] = None,
    unclassified: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    ids: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Bulk delete transactions by filter conditions or by IDs.

    If `ids` is provided (comma-separated), delete those specific records.
    Otherwise, delete all records matching the filter conditions.
    """
    conditions = []

    if ids:
        id_list = [int(i) for i in ids.split(",") if i.strip()]
        if not id_list:
            return {"deleted": 0}
        conditions.append(Transaction.id.in_(id_list))
    else:
        if entity:
            conditions.append(Transaction.entity == entity)
        if account:
            conditions.append(Transaction.account == account)
        if ccy:
            conditions.append(Transaction.ccy == ccy)
        if management:
            conditions.append(Transaction.management == management)
        if grouping:
            conditions.append(Transaction.grouping == grouping)
        if unclassified:
            conditions.append(Transaction.management.is_(None))
        if start_date:
            conditions.append(Transaction.period >= start_date)
        if end_date:
            conditions.append(Transaction.period <= end_date)
        if search:
            like = f"%{search}%"
            conditions.append(
                Transaction.abstract.ilike(like) | Transaction.counterpart.ilike(like)
            )

    if not conditions:
        raise HTTPException(status_code=400, detail="必须指定至少一个筛选条件")

    where = and_(*conditions)

    # Count first
    count_q = select(func.count()).select_from(Transaction).where(where)
    count = (await db.execute(count_q)).scalar() or 0

    # Delete
    await db.execute(delete(Transaction).where(where))

    return {"deleted": count}
