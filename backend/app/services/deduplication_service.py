"""Deduplication service: multi-field hash for duplicate detection."""
import hashlib
from datetime import date
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.transaction import Transaction


def compute_dedup_hash(
    entity: str, account: str, period: date,
    cf: float | None, abstract: str | None, counterpart: str | None
) -> str:
    cf_str = f"{cf:.2f}" if cf is not None else "0.00"
    raw = f"{entity}|{account}|{period.isoformat()}|{cf_str}|{abstract or ''}|{counterpart or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DeduplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_existing_hashes(self) -> Set[str]:
        result = await self.db.execute(
            select(Transaction.dedup_hash).where(Transaction.dedup_hash.isnot(None))
        )
        return {row for row in result.scalars().all()}

    async def filter_duplicates(self, records: List[dict]) -> tuple[List[dict], List[dict]]:
        """Return (new_records, duplicate_records)."""
        existing = await self.get_existing_hashes()

        new_records = []
        duplicates = []

        seen_in_batch: Set[str] = set()

        for rec in records:
            h = compute_dedup_hash(
                rec["entity"], rec["account"], rec["period"],
                rec["cf"], rec.get("abstract"), rec.get("counterpart"),
            )
            rec["dedup_hash"] = h

            if h in existing or h in seen_in_batch:
                duplicates.append(rec)
            else:
                new_records.append(rec)
                seen_in_batch.add(h)

        return new_records, duplicates
