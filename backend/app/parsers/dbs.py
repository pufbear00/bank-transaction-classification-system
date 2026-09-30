"""DBS Bank parser."""
import pandas as pd
from typing import List, Dict, Any
from app.parsers.base import BaseBankParser


class DBSParser(BaseBankParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_excel(file_path, header=None)

        header_row = None
        for idx in range(min(10, len(df))):
            if "Date" in str(df.iloc[idx].values):
                header_row = idx
                break
        if header_row is None:
            raise ValueError("无法找到DBS流水表头")

        df = pd.read_excel(file_path, header=header_row)
        df = df[df["Date"].notna()]
        df = df[~df["Date"].astype(str).str.contains("Printed", na=False)]

        records: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            period = pd.to_datetime(row.get("Date"), format="%d-%b-%Y", errors="coerce")
            if pd.isna(period):
                continue

            desc1 = str(row.get("Transaction Description 1", "") or "")
            desc2 = str(row.get("Transaction Description 2", "") or "")
            abstract = f"{desc1} {desc2}".strip()

            debit_raw = pd.to_numeric(row.get("Debit"), errors="coerce")
            credit_raw = pd.to_numeric(row.get("Credit"), errors="coerce")
            debit = 0.0 if pd.isna(debit_raw) else float(debit_raw)
            credit = 0.0 if pd.isna(credit_raw) else float(credit_raw)
            cf = credit - debit

            records.append({
                "period": period.date(),
                "abstract": abstract,
                "counterpart": self.extract_counterpart_from_description(abstract),
                "ccy": "SGD",
                "cf": float(cf),
                "bal": float(pd.to_numeric(row.get("Running Balance"), errors="coerce")) if not pd.isna(pd.to_numeric(row.get("Running Balance"), errors="coerce")) else 0.0,
                "note": None,
            })

        return records
