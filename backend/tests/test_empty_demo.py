"""Offline smoke checks. All generated records/database live in pytest's tempdir."""
import socket
import sqlite3
from pathlib import Path


def test_empty_isolated_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid.example/never-connect")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-ignored-test-value")
    from app.config import settings
    assert settings.DATABASE_URL.startswith("sqlite+aiosqlite:///")
    assert settings.OFFLINE_DEMO is True
    assert not hasattr(settings, "ANTHROPIC_API_KEY")
    assert Path(settings.UPLOAD_DIR).parts[-2:] == (".local", "uploads")

    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))

    attempts = []
    def deny_network(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Unexpected outbound network attempt")
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        assert client.get("/health").json()["external_sync"] is False
        with sqlite3.connect(db_path) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            assert len(tables) >= 8
            for table in tables:
                assert conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 0
        for endpoint in ["bank-accounts", "categories", "classification-rules", "import-templates", "exchange-rates", "amortizations"]:
            response = client.get(f"/api/v1/{endpoint}")
            assert response.status_code == 200, endpoint
            assert response.json() == [], endpoint
        transactions = client.get("/api/v1/transactions").json()
        assert transactions["items"] == [] and transactions["total"] == 0
        for endpoint in ["monthly-summary?year=2099", "cash-balance", "cash-balance-yearly?year=2099"]:
            assert client.get(f"/api/v1/reports/{endpoint}").status_code == 200
        assert client.post("/api/v1/exchange-rates/sync").status_code == 403
        account = {"entity": "虚构演示主体", "account": "演示账户", "ccy": "CNY"}
        assert client.post("/api/v1/bank-accounts", json=account).status_code == 200
        transaction = {"entity": "虚构演示主体", "account": "演示账户", "ccy": "CNY",
                       "period": "2099-01-02", "cf": -12.34, "abstract": "纯虚构测试交易"}
        response = client.post("/api/v1/transactions", json=transaction)
        assert response.status_code == 200, response.text
        assert response.json()["cf_in_cny"] == -12.34
        foreign = {**transaction, "ccy": "USD", "cf": -1}
        assert client.post("/api/v1/transactions", json=foreign).status_code == 409
        rate = {"date": "2099-01-02", "from_ccy": "USD", "to_ccy": "CNY", "rate": 7}
        assert client.post("/api/v1/exchange-rates", json=rate).status_code == 200
        assert client.post("/api/v1/transactions", json=foreign).json()["cf_in_cny"] == -7
        assert client.get("/api/v1/transactions").json()["total"] == 2
        assert client.get("/api/v1/reports/monthly-summary?year=2099").status_code == 200
        exported = client.get("/api/v1/transactions/export")
        assert exported.status_code == 200 and exported.content.startswith(b"PK")
        assert not attempts
