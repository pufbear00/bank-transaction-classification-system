from fastapi import APIRouter

from app.api.transactions import router as transactions_router
from app.api.imports import router as imports_router
from app.api.categories import router as categories_router
from app.api.bank_accounts import router as bank_accounts_router
from app.api.classification_rules import router as classification_rules_router
from app.api.import_templates import router as import_templates_router
from app.api.exchange_rates import router as exchange_rates_router
from app.api.reports import router as reports_router
from app.api.amortizations import router as amortizations_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(transactions_router)
api_router.include_router(imports_router)
api_router.include_router(categories_router)
api_router.include_router(bank_accounts_router)
api_router.include_router(classification_rules_router)
api_router.include_router(import_templates_router)
api_router.include_router(exchange_rates_router)
api_router.include_router(reports_router)
api_router.include_router(amortizations_router)
