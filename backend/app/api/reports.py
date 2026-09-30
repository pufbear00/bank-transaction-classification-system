"""Reports API: monthly summary pivot by management."""
import calendar
import io
import math
from datetime import date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, case, literal_column, and_, desc
from collections import defaultdict


def _safe_float(v) -> float:
    """Convert to float, treating None/NaN/Inf as 0."""
    if v is None:
        return 0.0
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return 0.0
    return f

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.models.bank_account import BankAccount
from app.models.exchange_rate import ExchangeRate
from app.models.account_balance import AccountBalance

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly-summary")
async def monthly_summary(
    year: int = Query(...),
    entity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a pivot table like the Management sheet:
    rows = grouping → class_name → management
    columns = monthly periods
    values = sum(cf_in_cny)
    """
    conditions = [extract("year", Transaction.period) == year]
    if entity:
        conditions.append(Transaction.entity == entity)

    month_expr = func.strftime("%Y-%m", Transaction.period)

    q = (
        select(
            Transaction.grouping,
            Transaction.class_name,
            Transaction.management,
            month_expr.label("month"),
            func.sum(Transaction.cf_in_cny).label("total"),
        )
        .where(*conditions)
        .where(Transaction.management.isnot(None))
        .group_by(
            Transaction.grouping,
            Transaction.class_name,
            Transaction.management,
            month_expr,
        )
    )
    result = await db.execute(q)
    rows = result.all()

    # Also get unclassified totals by month
    q_unclassified = (
        select(
            month_expr.label("month"),
            func.sum(Transaction.cf_in_cny).label("total"),
        )
        .where(*conditions)
        .where(Transaction.management.is_(None))
        .group_by(month_expr)
    )
    unclassified_result = await db.execute(q_unclassified)
    unclassified_rows = unclassified_result.all()

    # Collect all months
    months_set = set()
    for r in rows:
        months_set.add(r.month)
    for r in unclassified_rows:
        months_set.add(r.month)
    months = sorted(months_set)

    # DB field mapping:
    #   class_name (DB) = Grouping L1 in Excel (e.g. 02_经常性费用)
    #   grouping   (DB) = Class L2 in Excel    (e.g. 06_通信/云服务/软件)
    #   management (DB) = Management L3         (e.g. API-OpenAI)
    # Hierarchy: class_name → grouping → management
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
    for r in rows:
        l1 = r.class_name or "未分组"   # Grouping L1
        l2 = r.grouping or "未分类"      # Class L2
        l3 = r.management or "未分类"    # Management L3
        tree[l1][l2][l3][r.month] += _safe_float(r.total)

    # Build sorted sections (L1 → L2 → L3)
    sections = []
    for l1_name in sorted(tree.keys()):
        l2_map = tree[l1_name]
        l1_months = defaultdict(float)
        l1_active_months = set()
        class_list = []

        for l2_name in sorted(l2_map.keys()):
            l3_map = l2_map[l2_name]
            l2_months = defaultdict(float)
            l2_active_months = set()
            mgmt_list = []

            for l3_name in sorted(l3_map.keys()):
                month_data = l3_map[l3_name]
                grand = sum(month_data.values())
                mgmt_list.append({
                    "name": l3_name,
                    "months": {m: month_data.get(m, 0) for m in months},
                    "active_months": sorted(month_data.keys()),
                    "total": grand,
                })
                l2_active_months.update(month_data.keys())
                for m in months:
                    l2_months[m] += month_data.get(m, 0)

            l2_grand = sum(l2_months.values())
            class_list.append({
                "name": l2_name,
                "months": {m: l2_months[m] for m in months},
                "active_months": sorted(l2_active_months),
                "total": l2_grand,
                "items": mgmt_list,
            })
            l1_active_months.update(l2_active_months)
            for m in months:
                l1_months[m] += l2_months[m]

        l1_grand = sum(l1_months.values())
        sections.append({
            "name": l1_name,
            "months": {m: l1_months[m] for m in months},
            "active_months": sorted(l1_active_months),
            "total": l1_grand,
            "classes": class_list,
        })

    # Grand total
    grand_months = defaultdict(float)
    grand_active_months = set()
    for s in sections:
        grand_active_months.update(s["active_months"])
        for m in months:
            grand_months[m] += s["months"].get(m, 0)

    # 损益合计：排除非损益分组（98_非损益、99_内部往来 等 9x 开头），
    # 这样摊销费用不会被预付科目对冲掉，6-12 月也能体现出来。
    pnl_months = defaultdict(float)
    pnl_active_months = set()
    for s in sections:
        if (s["name"] or "").startswith(("98", "99")):
            continue
        pnl_active_months.update(s["active_months"])
        for m in months:
            pnl_months[m] += s["months"].get(m, 0)

    # Unclassified
    unclassified_months = {}
    for r in unclassified_rows:
        unclassified_months[r.month] = _safe_float(r.total)

    return {
        "year": year,
        "months": months,
        "sections": sections,
        "grand_total": {
            "months": {m: grand_months[m] for m in months},
            "active_months": sorted(grand_active_months),
            "total": sum(grand_months.values()),
        },
        "pnl_total": {
            "months": {m: pnl_months[m] for m in months},
            "active_months": sorted(pnl_active_months),
            "total": sum(pnl_months.values()),
        },
        "unclassified": {
            "months": {m: unclassified_months.get(m, 0) for m in months},
            "active_months": sorted(unclassified_months.keys()),
            "total": sum(unclassified_months.values()),
        },
    }


@router.get("/monthly-summary/export")
async def export_monthly_summary(
    year: int = Query(...),
    entity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Export monthly summary as XLSX."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, numbers

    # Reuse the same logic
    data = await monthly_summary(year=year, entity=entity, db=db)
    months = data["months"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Management"

    # Styles
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    grouping_font = Font(bold=True, size=11)
    grouping_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    class_font = Font(bold=True)
    class_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    num_fmt = '#,##0'

    # Header row
    ws.cell(row=1, column=1, value="求和项:CF in CNY").font = header_font
    ws.cell(row=1, column=1).fill = header_fill
    for ci, m in enumerate(months, 2):
        cell = ws.cell(row=1, column=ci, value=m)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    total_col = len(months) + 2
    ws.cell(row=1, column=total_col, value="总计").font = header_font
    ws.cell(row=1, column=total_col).fill = header_fill

    row_idx = 2
    for section in data["sections"]:
        # Grouping row
        ws.cell(row=row_idx, column=1, value=section["name"]).font = grouping_font
        for ci, m in enumerate(months, 2):
            c = ws.cell(row=row_idx, column=ci, value=section["months"].get(m, 0))
            c.number_format = num_fmt
            c.font = grouping_font
        c = ws.cell(row=row_idx, column=total_col, value=section["total"])
        c.number_format = num_fmt
        c.font = grouping_font
        for ci in range(1, total_col + 1):
            ws.cell(row=row_idx, column=ci).fill = grouping_fill
        row_idx += 1

        for cls in section["classes"]:
            # Class row
            ws.cell(row=row_idx, column=1, value=f"  {cls['name']}").font = class_font
            for ci, m in enumerate(months, 2):
                c = ws.cell(row=row_idx, column=ci, value=cls["months"].get(m, 0))
                c.number_format = num_fmt
                c.font = class_font
            c = ws.cell(row=row_idx, column=total_col, value=cls["total"])
            c.number_format = num_fmt
            c.font = class_font
            for ci in range(1, total_col + 1):
                ws.cell(row=row_idx, column=ci).fill = class_fill
            row_idx += 1

            for item in cls["items"]:
                # Management row
                ws.cell(row=row_idx, column=1, value=f"    {item['name']}")
                for ci, m in enumerate(months, 2):
                    c = ws.cell(row=row_idx, column=ci, value=item["months"].get(m, 0))
                    c.number_format = num_fmt
                c = ws.cell(row=row_idx, column=total_col, value=item["total"])
                c.number_format = num_fmt
                row_idx += 1

    # Grand total
    ws.cell(row=row_idx, column=1, value="总计").font = Font(bold=True, size=12)
    for ci, m in enumerate(months, 2):
        c = ws.cell(row=row_idx, column=ci, value=data["grand_total"]["months"].get(m, 0))
        c.number_format = num_fmt
        c.font = Font(bold=True, size=12)
    c = ws.cell(row=row_idx, column=total_col, value=data["grand_total"]["total"])
    c.number_format = num_fmt
    c.font = Font(bold=True, size=12)

    # 损益合计（排除 98_非损益 / 99_内部往来，让摊销费用在 6-12 月体现）
    row_idx += 1
    pnl = data.get("pnl_total", {"months": {}, "total": 0})
    pnl_font = Font(bold=True, size=12)
    pnl_fill = PatternFill(start_color="FFF7CC", end_color="FFF7CC", fill_type="solid")
    ws.cell(row=row_idx, column=1, value="损益合计（不含非损益）").font = pnl_font
    for ci, m in enumerate(months, 2):
        c = ws.cell(row=row_idx, column=ci, value=pnl["months"].get(m, 0))
        c.number_format = num_fmt
        c.font = pnl_font
    c = ws.cell(row=row_idx, column=total_col, value=pnl["total"])
    c.number_format = num_fmt
    c.font = pnl_font
    for ci in range(1, total_col + 1):
        ws.cell(row=row_idx, column=ci).fill = pnl_fill

    # Column widths
    ws.column_dimensions["A"].width = 30
    for ci in range(2, total_col + 1):
        ws.column_dimensions[ws.cell(row=1, column=ci).column_letter].width = 16

    from fastapi.responses import StreamingResponse
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=management_report_{year}.xlsx"},
    )


@router.get("/cash-balance")
async def cash_balance(
    date: Optional[str] = Query(None, description="截至日期 YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
):
    """
    Cash balance overview: for each bank account, find the latest transaction
    balance (bal) up to the given date, then convert to CNY using the latest
    exchange rate up to that date.
    """
    import datetime

    if date:
        target_date = datetime.date.fromisoformat(date)
    else:
        target_date = datetime.date.today()

    # 1. Get all bank accounts
    acct_result = await db.execute(
        select(BankAccount).order_by(BankAccount.entity, BankAccount.account)
    )
    accounts = acct_result.scalars().all()

    result_accounts = []
    total_cny = 0.0

    for acct in accounts:
        # 2. 优先从 account_balances 表读手动余额
        ab_q = (
            select(AccountBalance.balance, AccountBalance.period)
            .where(
                and_(
                    AccountBalance.entity == acct.entity,
                    AccountBalance.account == acct.account,
                    AccountBalance.period <= target_date,
                )
            )
            .order_by(desc(AccountBalance.period))
            .limit(1)
        )
        ab_result = await db.execute(ab_q)
        ab_row = ab_result.first()

        balance = None
        balance_date = None
        if ab_row:
            balance = _safe_float(ab_row.balance)
            balance_date = ab_row.period.isoformat() if ab_row.period else None
        else:
            # 回退：从交易表的 bal 字段读
            txn_q = (
                select(Transaction.bal, Transaction.period)
                .where(
                    and_(
                        Transaction.entity == acct.entity,
                        Transaction.account == acct.account,
                        Transaction.period <= target_date,
                        Transaction.bal.isnot(None),
                    )
                )
                .order_by(desc(Transaction.period), desc(Transaction.id))
                .limit(1)
            )
            txn_result = await db.execute(txn_q)
            txn_row = txn_result.first()
            if txn_row:
                balance = _safe_float(txn_row.bal)
                balance_date = txn_row.period.isoformat() if txn_row.period else None

        # 3. Get exchange rate
        if acct.ccy == "CNY":
            exchange_rate = 1.0
        else:
            rate_q = (
                select(ExchangeRate.rate)
                .where(
                    and_(
                        ExchangeRate.from_ccy == acct.ccy,
                        ExchangeRate.to_ccy == "CNY",
                        ExchangeRate.date <= target_date,
                    )
                )
                .order_by(desc(ExchangeRate.date))
                .limit(1)
            )
            rate_result = await db.execute(rate_q)
            rate_row = rate_result.scalar()
            exchange_rate = _safe_float(rate_row) if rate_row else 0.0

        balance_cny = (balance * exchange_rate) if balance is not None else 0.0
        total_cny += balance_cny

        result_accounts.append({
            "account_id": acct.id,
            "entity": acct.entity,
            "account": acct.account,
            "ccy": acct.ccy,
            "balance": balance,
            "balance_date": balance_date,
            "exchange_rate": round(exchange_rate, 6),
            "balance_cny": round(balance_cny, 2),
        })

    return {
        "date": target_date.isoformat(),
        "accounts": result_accounts,
        "total_cny": round(total_cny, 2),
    }


@router.get("/cash-balance-yearly")
async def cash_balance_yearly(
    year: int = Query(..., description="年份，如 2026"),
    db: AsyncSession = Depends(get_db),
):
    """
    Cash balance yearly view: for each bank account, find the latest balance
    per month within the given year, then convert to CNY.
    """
    import datetime

    # 1. Get all bank accounts
    acct_result = await db.execute(
        select(BankAccount).order_by(BankAccount.entity, BankAccount.account)
    )
    accounts = acct_result.scalars().all()

    year_start = datetime.date(year, 1, 1)
    year_end = datetime.date(year, 12, 31)

    # 2. For each account, query all transactions with bal in this year, grouped by month
    result_accounts = []
    all_months_with_data = set()
    monthly_totals_cny: defaultdict[str, float] = defaultdict(float)

    for acct in accounts:
        # 2a. 优先从 account_balances 表读手动余额
        ab_q = (
            select(AccountBalance.balance, AccountBalance.period)
            .where(
                and_(
                    AccountBalance.entity == acct.entity,
                    AccountBalance.account == acct.account,
                    AccountBalance.period >= year_start,
                    AccountBalance.period <= year_end,
                )
            )
            .order_by(AccountBalance.period)
        )
        ab_result = await db.execute(ab_q)
        ab_rows = ab_result.all()

        # 手动余额按月索引
        manual_balances: dict[int, tuple[datetime.date, float]] = {}
        for row in ab_rows:
            manual_balances[row.period.month] = (row.period, _safe_float(row.balance))

        # 2b. 从交易表补充没有手动余额的月份
        txn_q = (
            select(
                Transaction.id,
                Transaction.bal,
                Transaction.period,
            )
            .where(
                and_(
                    Transaction.entity == acct.entity,
                    Transaction.account == acct.account,
                    Transaction.period >= year_start,
                    Transaction.period <= year_end,
                    Transaction.bal.isnot(None),
                )
            )
            .order_by(Transaction.period, Transaction.id)
        )
        txn_result = await db.execute(txn_q)
        txn_rows = txn_result.all()

        # Group by month: take the latest date, then max id
        month_best: dict[int, tuple[datetime.date, int, float]] = {}
        for row in txn_rows:
            m = row.period.month
            bal = _safe_float(row.bal)
            current = month_best.get(m)
            if current is None or (row.period, row.id) > (current[0], current[1]):
                month_best[m] = (row.period, row.id, bal)

        # Build balances dict — manual overrides take priority
        balances: dict[str, dict] = {}
        all_months = set(manual_balances.keys()) | set(month_best.keys())
        for m in all_months:
            month_key = f"{year}-{m:02d}"
            all_months_with_data.add(month_key)

            _, last_day = calendar.monthrange(year, m)

            if m in manual_balances:
                bal_date, bal = manual_balances[m]
                txn_id = None
            else:
                bal_date, txn_id, bal = month_best[m]

            is_month_end = bal_date.day == last_day

            # Get exchange rate
            if acct.ccy == "CNY":
                exchange_rate = 1.0
            else:
                rate_date = datetime.date(year, m, last_day)
                rate_q = (
                    select(ExchangeRate.rate)
                    .where(
                        and_(
                            ExchangeRate.from_ccy == acct.ccy,
                            ExchangeRate.to_ccy == "CNY",
                            ExchangeRate.date <= rate_date,
                        )
                    )
                    .order_by(desc(ExchangeRate.date))
                    .limit(1)
                )
                rate_result = await db.execute(rate_q)
                rate_row = rate_result.scalar()
                exchange_rate = _safe_float(rate_row) if rate_row else 0.0

            balance_cny = round(bal * exchange_rate, 2)
            monthly_totals_cny[month_key] += balance_cny

            balances[month_key] = {
                "balance": bal,
                "balance_date": bal_date.isoformat(),
                "is_month_end": is_month_end,
                "exchange_rate": round(exchange_rate, 6),
                "balance_cny": balance_cny,
                "transaction_id": txn_id,
            }

        result_accounts.append({
            "account_id": acct.id,
            "entity": acct.entity,
            "account": acct.account,
            "ccy": acct.ccy,
            "balances": balances,
        })

    # Build months list (only months with data, sorted)
    months = sorted(all_months_with_data)

    # Latest total CNY = the last month with data
    total_cny_latest = round(monthly_totals_cny[months[-1]], 2) if months else 0.0

    return {
        "year": year,
        "months": months,
        "accounts": result_accounts,
        "monthly_totals_cny": {m: round(monthly_totals_cny[m], 2) for m in months},
        "total_cny_latest": total_cny_latest,
    }
