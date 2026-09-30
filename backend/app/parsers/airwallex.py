"""Airwallex parser."""
import pandas as pd
from typing import List, Dict, Any
from app.parsers.base import BaseBankParser


class AirwallexParser(BaseBankParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_excel(file_path)

        records: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            period = pd.to_datetime(row.get("Time"), errors="coerce")
            if pd.isna(period):
                continue
            if period.tzinfo is not None:
                period = period.tz_localize(None)

            description = str(row.get("Description", ""))
            txn_id = str(row.get("Transaction Id", "")) if pd.notna(row.get("Transaction Id")) else ""

            def _parse_num(val):
                if isinstance(val, str):
                    val = val.replace(",", "")
                v = pd.to_numeric(val, errors="coerce")
                return 0.0 if pd.isna(v) else float(v)

            amount = _parse_num(row.get("Amount"))
            debit = _parse_num(row.get("Debit Net Amount"))
            credit = _parse_num(row.get("Credit Net Amount"))

            if debit + credit > 0:
                cf = credit - debit
            else:
                cf = -amount

            bal_str = str(row.get("Account Balance", "0")).replace(",", "")
            try:
                bal = float(bal_str)
            except ValueError:
                bal = 0

            # Append transaction ID to abstract to ensure uniqueness for dedup hash
            abstract = f"{description} [{txn_id}]" if txn_id else description

            records.append({
                "period": period.date(),
                "abstract": abstract,
                "counterpart": self.extract_counterpart_from_description(description),
                "ccy": str(row.get("Wallet Currency", "USD")),
                "cf": float(cf),
                "bal": float(bal),
                "note": str(row.get("Note to Self", "")) if not pd.isna(row.get("Note to Self", None)) else None,
            })

        return records
