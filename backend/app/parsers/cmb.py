"""招商银行 (China Merchants Bank) parser."""
import pandas as pd
from typing import List, Dict, Any
from app.parsers.base import BaseBankParser


class CMBParser(BaseBankParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_excel(file_path, header=None)

        header_row = None
        for idx in range(min(20, len(df))):
            if "交易日" in str(df.iloc[idx].values):
                header_row = idx
                break
        if header_row is None:
            raise ValueError("无法找到招商银行流水表头")

        df = pd.read_excel(file_path, header=header_row)

        records: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            period = pd.to_datetime(row.get("交易日"), format="%Y-%m-%d", errors="coerce")
            if pd.isna(period):
                continue

            abstract_parts = [str(row.get("摘要", "") or "")]
            usage = row.get("用途")
            if usage and not pd.isna(usage):
                abstract_parts.append(str(usage))
            abstract = " ".join(abstract_parts).strip()

            debit_raw = pd.to_numeric(row.get("借方金额"), errors="coerce")
            credit_raw = pd.to_numeric(row.get("贷方金额"), errors="coerce")
            debit = 0.0 if pd.isna(debit_raw) else float(debit_raw)
            credit = 0.0 if pd.isna(credit_raw) else float(credit_raw)
            cf = credit - debit

            records.append({
                "period": period.date(),
                "abstract": abstract,
                "counterpart": row.get("收(付)方名称") if not pd.isna(row.get("收(付)方名称", None)) else None,
                "ccy": self.normalize_currency(str(row.get("币种", "CNY"))),
                "cf": float(cf),
                "bal": float(pd.to_numeric(row.get("余额"), errors="coerce")) if not pd.isna(pd.to_numeric(row.get("余额"), errors="coerce")) else 0.0,
                "note": str(row.get("扩展摘要", "")) if not pd.isna(row.get("扩展摘要", None)) else None,
            })

        return records
