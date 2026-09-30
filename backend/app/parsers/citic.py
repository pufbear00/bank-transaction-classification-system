"""中信银行 (CITIC Bank) parser."""
import pandas as pd
from typing import List, Dict, Any
from app.parsers.base import BaseBankParser


class CITICParser(BaseBankParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_excel(file_path, header=None)

        header_row = None
        for idx in range(min(20, len(df))):
            if "交易日期" in str(df.iloc[idx].values):
                header_row = idx
                break
        if header_row is None:
            raise ValueError("无法找到中信银行流水表头")

        df = pd.read_excel(file_path, header=header_row)

        records: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            period = pd.to_datetime(row.get("交易日期"), format="%Y-%m-%d", errors="coerce")
            if pd.isna(period):
                continue

            debit_raw = row.get("借方发生额")
            credit_raw = row.get("贷方发生额")
            # Handle string values with commas (e.g. "23,975.20")
            if isinstance(debit_raw, str):
                debit_raw = debit_raw.replace(",", "")
            if isinstance(credit_raw, str):
                credit_raw = credit_raw.replace(",", "")
            debit_val = pd.to_numeric(debit_raw, errors="coerce")
            credit_val = pd.to_numeric(credit_raw, errors="coerce")
            debit = 0.0 if pd.isna(debit_val) else float(debit_val)
            credit = 0.0 if pd.isna(credit_val) else float(credit_val)
            cf = credit - debit

            bal_raw = row.get("账户余额")
            if isinstance(bal_raw, str):
                bal_raw = bal_raw.replace(",", "")
            bal_val = pd.to_numeric(bal_raw, errors="coerce")
            bal = 0.0 if pd.isna(bal_val) else float(bal_val)

            # Currency: use column if exists, otherwise default CNY
            ccy_val = row.get("币种")
            if ccy_val is not None and not pd.isna(ccy_val):
                ccy = self.normalize_currency(str(ccy_val))
            else:
                ccy = "CNY"

            # Append 柜员交易号 to abstract for dedup uniqueness
            abstract = str(row.get("摘要", "")) if not pd.isna(row.get("摘要", None)) else ""
            txn_no = str(row.get("柜员交易号", "")) if not pd.isna(row.get("柜员交易号", None)) else ""
            if txn_no:
                abstract = f"{abstract} [{txn_no}]"

            records.append({
                "period": period.date(),
                "abstract": abstract,
                "counterpart": str(row.get("对方账户名称", "")) if not pd.isna(row.get("对方账户名称", None)) else None,
                "ccy": ccy,
                "cf": float(cf),
                "bal": float(bal),
                "note": str(row.get("附言", "")) if not pd.isna(row.get("附言", None)) else None,
            })

        # CITIC statements list newest-first; reverse to chronological order
        # so that the latest transaction per day gets the highest DB id.
        records.reverse()
        return records
