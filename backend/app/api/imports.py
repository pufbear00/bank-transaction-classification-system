"""Import API: batch upload+parse → confirm."""
import os
import uuid
import math
import shutil
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


def _clean_record(rec: dict) -> dict:
    """Replace NaN/Inf floats with None so JSON serialization works."""
    for k, v in rec.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            rec[k] = None
    return rec

from app.dependencies import get_db
from app.config import settings
from app.services.import_pipeline import ImportPipeline
from app.schemas.import_schema import ConfirmImportRequest, ConfirmImportResponse

router = APIRouter(prefix="/import", tags=["import"])

BANK_TYPE_LABELS = {"cmb": "招商银行", "citic": "中信银行", "airwallex": "Airwallex", "dbs": "DBS"}


@router.post("/batch-parse")
async def batch_upload_and_parse(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple files, auto-detect bank type, parse all, return combined preview."""
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    pipeline = ImportPipeline(db)
    all_records: list = []
    file_summaries: list = []
    errors: list = []

    for f in files:
        original = os.path.basename((f.filename or "file.xlsx").replace("\\", "/"))
        saved_name = f"{uuid.uuid4().hex[:8]}_{original}"
        saved_path = os.path.join(upload_dir, saved_name)

        with open(saved_path, "wb") as out:
            shutil.copyfileobj(f.file, out)

        try:
            result = await pipeline.parse_file(saved_path, bank_type=None)
            # Clean records for JSON serialization
            for rec in result["records"]:
                if isinstance(rec.get("period"), date):
                    rec["period"] = rec["period"].isoformat()
                _clean_record(rec)

            all_records.extend(result["records"])
            file_summaries.append({
                "filename": original,
                "bank_type": result["bank_type"],
                "bank_label": BANK_TYPE_LABELS.get(result["bank_type"], result["bank_type"]),
                "entity": result["entity"],
                "account": result["account"],
                "count": result["total"],
            })
        except Exception as e:
            errors.append({"filename": original, "error": str(e)})

    return {
        "files": file_summaries,
        "records": all_records,
        "total": len(all_records),
        "errors": errors,
    }


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a single bank statement file (kept for backwards compat)."""
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    original = os.path.basename((file.filename or "file.xlsx").replace("\\", "/"))
    saved_name = f"{uuid.uuid4().hex[:8]}_{original}"
    saved_path = os.path.join(upload_dir, saved_name)

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {
        "filename": original,
        "saved_path": saved_path,
        "size": os.path.getsize(saved_path),
    }


@router.post("/confirm", response_model=ConfirmImportResponse)
async def confirm_import(
    data: ConfirmImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Confirm import: dedup → classify → exchange rate → save."""
    for rec in data.records:
        if isinstance(rec.get("period"), str):
            rec["period"] = date.fromisoformat(rec["period"])
        # Ensure cf is numeric
        if rec.get("cf") is None:
            rec["cf"] = 0

    pipeline = ImportPipeline(db)
    result = await pipeline.confirm_import(
        records=data.records,
        entity=data.entity,
        account=data.account,
    )
    return ConfirmImportResponse(**result)
