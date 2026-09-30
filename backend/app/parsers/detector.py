"""Auto-detect bank type and extract entity/account from filename + content.

Primary strategy: scan file content for known bank account numbers and match
against the bank_accounts table. Falls back to filename heuristics.
"""
import os
import re
import pandas as pd
from typing import Tuple, List, Dict, Any


def detect_bank_type(file_path: str) -> str:
    filename = os.path.basename(file_path).lower()

    # Step 1: filename keywords
    if "airwallex" in filename:
        return "airwallex"
    if "dbs" in filename:
        return "dbs"
    if "招商" in filename or "cmb" in filename:
        return "cmb"
    if "中信" in filename or "citic" in filename:
        return "citic"

    # Step 2: scan file content — look for bank name in transaction rows
    try:
        df = pd.read_excel(file_path, header=None, nrows=30)
        content = df.to_string()
        content_lower = content.lower()

        # 优先从"交易账号开户网点名称"等交易行中识别银行名称
        if "中信银行" in content:
            return "citic"
        if "招商银行" in content:
            return "cmb"
        if "airwallex" in content_lower or "wallet currency" in content_lower:
            return "airwallex"
        if "dbs" in content_lower:
            return "dbs"
        # 回退：表头关键词
        if "交易日期" in content:
            return "citic"
        if "交易日" in content or "对账单" in content:
            return "cmb"
    except Exception:
        pass

    raise ValueError("无法识别银行类型，请手动指定")


def _read_file_header(file_path: str) -> str:
    """Read the first 30 rows of an Excel file as a single string for matching."""
    try:
        df = pd.read_excel(file_path, header=None, nrows=30)
        return df.to_string()
    except Exception:
        return ""


def extract_entity_account(
    file_path: str,
    bank_accounts: List[Dict[str, Any]] | None = None,
) -> Tuple[str, str]:
    """Extract entity and account name from a bank statement file.

    Args:
        file_path: Path to the bank statement Excel file.
        bank_accounts: List of dicts with keys: entity, account, account_number, bank_type.
            If provided, will try to match account numbers found in file content.
    """
    filename = os.path.basename(file_path)
    content = _read_file_header(file_path)

    # --- Strategy 1: Match account number from file content against known accounts ---
    if bank_accounts:
        match = _match_by_account_number(content, filename, bank_accounts)
        if match:
            return match["entity"], match["account"]

    # --- Strategy 2: Filename + content heuristics (fallback) ---
    return _heuristic_entity_account(filename, content)


def _match_by_account_number(
    content: str,
    filename: str,
    bank_accounts: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    """Try to find a known account number in the file content or filename.

    Sort accounts by account_number length (longest first) to prefer more
    specific matches (prefixed account identifiers before their numeric suffixes).
    """
    # Combine filename and content for searching
    search_text = filename + " " + content

    # Sort by account_number length descending to match longest first
    sorted_accounts = sorted(
        [a for a in bank_accounts if a.get("account_number")],
        key=lambda a: len(a["account_number"]),
        reverse=True,
    )

    for acct in sorted_accounts:
        acct_num = acct["account_number"]
        # Match full account number or numeric part after known prefixes
        if acct_num in search_text:
            return acct
        for prefix in ("NRA", "FTN"):
            if acct_num.startswith(prefix):
                numeric_part = acct_num[len(prefix):]
                if numeric_part in search_text:
                    return acct

    return None


def _heuristic_entity_account(filename: str, content: str) -> Tuple[str, str]:
    """Fallback: infer entity/account from filename and content heuristics."""

    # --- Entity ---
    entity = _detect_entity(filename, content)

    # --- Account ---
    account = ""
    lower = filename.lower()

    if "airwallex" in lower:
        account = "airwallex-SGD" if "sgd" in lower else "airwallex-USD"
    elif "dbs" in lower:
        account = "DBS"
    elif "招商" in filename:
        if "美金" in filename or "USD" in filename.upper():
            if "资本金" in filename:
                account = "招商资本金USD"
            else:
                account = "招商基本户USD"
        elif "结汇待支付" in filename:
            account = "招商结汇待支付CNY"
        else:
            account = "招商基本户CNY"
    elif "中信" in filename:
        if "FTN" in filename.upper():
            account = "中信多币种账户-FTN"
        elif "NRA" in filename.upper():
            account = "中信基本户-NRA"
        else:
            account = "中信基本户USD"

    # If no account matched from filename, try detecting bank type and guess
    if not account:
        try:
            bank_type = detect_bank_type(filename)
        except ValueError:
            bank_type = None

        if bank_type == "citic":
            if "FTN" in content:
                account = "中信多币种账户-FTN"
            elif "NRA" in content:
                account = "中信基本户-NRA"
            else:
                account = "中信基本户USD"
        elif bank_type == "cmb":
            account = "招商基本户CNY"
        elif bank_type == "airwallex":
            account = "airwallex-USD"
        elif bank_type == "dbs":
            account = "DBS"

    return entity, account or "未知账户"


def _detect_entity(filename: str, content: str) -> str:
    """No company presets: the user must choose an entity for unrecognized data."""
    return "未指定主体"
