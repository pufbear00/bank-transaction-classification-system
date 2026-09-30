"""Amortization API: create, list, detail, delete."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.amortization import (
    AmortizationCreate,
    AmortizationResponse,
    AmortizationDetailResponse,
    AmortizationEntryResponse,
)
from app.services.amortization_service import AmortizationService

router = APIRouter(prefix="/amortizations", tags=["amortizations"])


@router.get("", response_model=List[AmortizationResponse])
async def list_amortizations(db: AsyncSession = Depends(get_db)):
    svc = AmortizationService(db)
    items = await svc.list_amortizations()
    results = []
    for item in items:
        a = item["amortization"]
        resp = AmortizationResponse.model_validate(a)
        resp.posted_count = item["posted_count"]
        resp.total_entries = item["total_entries"]
        results.append(resp)
    return results


@router.post("", response_model=AmortizationDetailResponse)
async def create_amortization(
    body: AmortizationCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = AmortizationService(db)
    amort = await svc.create_amortization(
        entity=body.entity,
        total_amount=body.total_amount,
        start_date=body.start_date,
        months=body.months,
        prepaid_account=body.prepaid_account,
        expense_account=body.expense_account,
        grouping=body.grouping,
        class_name=body.class_name,
        source_transaction_id=body.source_transaction_id,
    )
    detail = await svc.get_amortization_detail(amort.id)
    a = detail["amortization"]
    resp = AmortizationDetailResponse.model_validate(a)
    resp.posted_count = detail["posted_count"]
    resp.total_entries = detail["total_entries"]
    resp.entries = [AmortizationEntryResponse.model_validate(e) for e in detail["entries"]]
    return resp


@router.get("/{amort_id}", response_model=AmortizationDetailResponse)
async def get_amortization_detail(
    amort_id: int,
    db: AsyncSession = Depends(get_db),
):
    svc = AmortizationService(db)
    detail = await svc.get_amortization_detail(amort_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Amortization not found")
    a = detail["amortization"]
    resp = AmortizationDetailResponse.model_validate(a)
    resp.posted_count = detail["posted_count"]
    resp.total_entries = detail["total_entries"]
    resp.entries = [AmortizationEntryResponse.model_validate(e) for e in detail["entries"]]
    return resp


@router.delete("/{amort_id}")
async def delete_amortization(
    amort_id: int,
    db: AsyncSession = Depends(get_db),
):
    svc = AmortizationService(db)
    deleted = await svc.delete_amortization(amort_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Amortization not found")
    return {"deleted": True}
