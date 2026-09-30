"""Import pipeline: orchestrates parse → dedup → classify → exchange rate → save."""
import uuid
from pathlib import Path
from app.config import settings
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.parsers import PARSERS, detect_bank_type, extract_entity_account
from app.services.deduplication_service import DeduplicationService
from app.services.classification_service import ClassificationService
from app.services.exchange_rate_service import ExchangeRateService
from app.models.transaction import Transaction
from app.models.bank_account import BankAccount


class ImportPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_bank_accounts(self) -> List[Dict[str, Any]]:
        """Load all bank accounts for account-number matching."""
        result = await self.db.execute(select(BankAccount))
        return [
            {
                "entity": a.entity,
                "account": a.account,
                "account_number": a.account_number,
                "bank_type": a.bank_type,
            }
            for a in result.scalars().all()
        ]

    async def parse_file(self, file_path: str, bank_type: str | None = None) -> Dict[str, Any]:
        """Parse file and return preview data."""
        path = Path(file_path).resolve()
        root = Path(settings.UPLOAD_DIR).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("仅允许读取本空数据版上传目录中的本地文件")
        file_path = str(path)
        if not bank_type:
            bank_type = detect_bank_type(file_path)

        bank_accounts = await self._load_bank_accounts()
        entity, account = extract_entity_account(file_path, bank_accounts=bank_accounts)

        parser_cls = PARSERS.get(bank_type)
        if not parser_cls:
            raise ValueError(f"不支持的银行类型: {bank_type}")

        parser = parser_cls()
        records = parser.parse(file_path)

        for rec in records:
            rec["entity"] = rec.get("entity") or entity
            rec["account"] = rec.get("account") or account

        return {
            "bank_type": bank_type,
            "entity": entity,
            "account": account,
            "total": len(records),
            "records": records,
        }

    async def confirm_import(
        self,
        records: List[Dict],
        entity: str | None = None,
        account: str | None = None,
    ) -> Dict[str, Any]:
        """Full import: dedup → classify → exchange rate → save."""
        batch_id = str(uuid.uuid4())[:8]

        # Override entity/account if provided
        if entity or account:
            for rec in records:
                if entity:
                    rec["entity"] = entity
                if account:
                    rec["account"] = account

        # 1. Deduplicate
        dedup_svc = DeduplicationService(self.db)
        new_records, duplicates = await dedup_svc.filter_duplicates(records)

        # 2. Classify
        cls_svc = ClassificationService(self.db)
        classified = await cls_svc.classify_batch(new_records)

        # 3. Exchange rates
        rate_svc = ExchangeRateService(self.db)
        for rec in classified:
            cf = rec.get("cf") or 0
            rec["cf"] = cf  # ensure not None
            ccy = rec.get("ccy", "CNY")
            period = rec.get("period")
            if ccy != "CNY" and period:
                rate = await rate_svc.get_rate(period, ccy)
                rec["exchange_rate"] = rate
                rec["cf_in_cny"] = cf * rate
            else:
                rec["exchange_rate"] = 1.0
                rec["cf_in_cny"] = cf

        # 4. Save to DB
        saved = []
        for rec in classified:
            txn = Transaction(
                entity=rec["entity"],
                account=rec["account"],
                counterpart=rec.get("counterpart"),
                period=rec["period"],
                abstract=rec.get("abstract"),
                ccy=rec.get("ccy", "CNY"),
                cf=rec["cf"],
                bal=rec.get("bal"),
                note=rec.get("note"),
                exchange_rate=rec.get("exchange_rate", 1.0),
                cf_in_cny=rec.get("cf_in_cny"),
                management=rec.get("management"),
                grouping=rec.get("grouping"),
                class_name=rec.get("class_name"),
                cf_line=rec.get("cf_line"),
                classification_method=rec.get("method"),
                classification_confidence=rec.get("confidence"),
                import_batch=batch_id,
                dedup_hash=rec.get("dedup_hash"),
            )
            self.db.add(txn)
            saved.append(txn)

        await self.db.flush()

        return {
            "batch_id": batch_id,
            "imported": len(saved),
            "duplicates": len(duplicates),
            "classified": sum(1 for r in classified if r.get("management")),
            "unclassified": sum(1 for r in classified if not r.get("management")),
        }
