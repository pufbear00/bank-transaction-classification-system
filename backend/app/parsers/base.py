"""Bank statement parser base class."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd


class BaseBankParser(ABC):
    """All parsers produce a list of dicts with these standard keys."""

    STANDARD_KEYS = [
        "entity", "account", "counterpart", "period",
        "abstract", "ccy", "cf", "bal", "note",
    ]

    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a bank statement file and return list of transaction dicts."""

    @staticmethod
    def normalize_currency(ccy: str) -> str:
        ccy = str(ccy).strip().upper()
        mapping = {
            "人民币": "CNY", "美元": "USD", "美金": "USD",
            "港币": "HKD", "新加坡元": "SGD", "新元": "SGD",
        }
        return mapping.get(ccy, ccy)

    @staticmethod
    def extract_counterpart_from_description(desc) -> str | None:
        if pd.isna(desc):
            return None
        parts = str(desc).split(",")
        return parts[0].strip() if parts else None
