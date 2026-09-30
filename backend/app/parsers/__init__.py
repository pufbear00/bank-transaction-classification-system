from app.parsers.cmb import CMBParser
from app.parsers.citic import CITICParser
from app.parsers.airwallex import AirwallexParser
from app.parsers.dbs import DBSParser
from app.parsers.detector import detect_bank_type, extract_entity_account

PARSERS = {
    "cmb": CMBParser,
    "citic": CITICParser,
    "airwallex": AirwallexParser,
    "dbs": DBSParser,
}

__all__ = ["PARSERS", "detect_bank_type", "extract_entity_account"]
