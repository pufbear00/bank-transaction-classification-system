"""Local keyword classification only. Rules are supplied by the demo user."""
from sqlalchemy import select
from app.models.classification_rule import ClassificationRule
from app.models.category_tree import CategoryNode


class ClassificationService:
    def __init__(self, db):
        self.db = db
        self._rules_cache = None

    async def _load_rules(self):
        if self._rules_cache is None:
            rows = await self.db.execute(select(ClassificationRule).order_by(ClassificationRule.match_count.desc()))
            self._rules_cache = list(rows.scalars().all())
        return self._rules_cache

    async def classify_transaction(self, abstract, counterpart=None, amount=None, entity=None):
        return await self._classify_by_keyword(abstract, counterpart)

    async def _classify_by_keyword(self, abstract, counterpart):
        if abstract:
            for rule in await self._load_rules():
                if rule.keyword and rule.keyword in f"{abstract} {counterpart or ''}":
                    rule.match_count = (rule.match_count or 0) + 1
                    return {"management": rule.management, "grouping": rule.grouping,
                            "class_name": rule.class_name, "cf_line": rule.cf_line,
                            "confidence": 1.0, "method": "keyword"}
        return self._empty("keyword", 0.0)

    async def classify_batch(self, transactions):
        return [{**txn, **await self.classify_transaction(
            txn.get("abstract", ""), txn.get("counterpart"), txn.get("cf"), txn.get("entity"))}
            for txn in transactions]

    async def add_learned_rule(self, keyword, management, grouping, class_name, cf_line):
        self.db.add(ClassificationRule(keyword=keyword, management=management,
                    grouping=grouping, class_name=class_name, cf_line=cf_line,
                    source="learned", match_count=1))
        self._rules_cache = None

    async def lookup_category(self, management_name):
        result = await self.db.execute(select(CategoryNode).where(
            CategoryNode.level == 3, CategoryNode.name == management_name))
        node = result.scalar_one_or_none()
        if not node:
            return None
        class_node = await self.db.get(CategoryNode, node.parent_id) if node.parent_id else None
        grouping_node = await self.db.get(CategoryNode, class_node.parent_id) if class_node and class_node.parent_id else None
        return {"management": node.name, "class_name": class_node.name if class_node else None,
                "grouping": grouping_node.name if grouping_node else None, "cf_line": node.cf_line}

    @staticmethod
    def _empty(method, confidence):
        return {"management": None, "grouping": None, "class_name": None,
                "cf_line": None, "confidence": confidence, "method": method}
