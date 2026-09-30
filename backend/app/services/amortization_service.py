"""Amortization service: create/delete amortization schedules and post ADJ transactions."""
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.amortization import Amortization, AmortizationEntry
from app.models.transaction import Transaction
from app.models.category_tree import CategoryNode


class AmortizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_amortization(
        self,
        entity: str,
        total_amount: float,
        start_date: date,
        months: int,
        prepaid_account: str,
        expense_account: str,
        grouping: str | None = None,
        class_name: str | None = None,
        source_transaction_id: int | None = None,
    ) -> Amortization:
        monthly_amount = round(total_amount / months, 2)

        # Auto-lookup grouping/class_name from expense_account if not provided
        if not grouping or not class_name:
            lookup = await self._lookup_category(expense_account)
            if lookup:
                grouping = grouping or lookup.get("grouping")
                class_name = class_name or lookup.get("class_name")

        # 确保费用科目 + 预付科目都登记进分类树，避免摊销与分类树对不上（两边映不起来）
        if grouping and class_name:
            await self._ensure_category_node(grouping, class_name, expense_account)
        # 预付科目固定挂在 98_非损益 下，cf_line 沿用现有预付账款节点的口径
        await self._ensure_category_node(
            "98_非损益", "98_非损益", prepaid_account,
            cf_line="支付其他与经营活动有关的现金",
        )

        amort = Amortization(
            source_transaction_id=source_transaction_id,
            entity=entity,
            total_amount=total_amount,
            start_date=start_date,
            months=months,
            monthly_amount=monthly_amount,
            prepaid_account=prepaid_account,
            expense_account=expense_account,
            grouping=grouping,
            class_name=class_name,
            status="active",
        )
        self.db.add(amort)
        await self.db.flush()

        # Generate entries and post each one
        base = date(start_date.year, start_date.month, 1)
        for i in range(months):
            period = base + relativedelta(months=i)
            # Last month gets the remainder to avoid rounding drift
            if i == months - 1:
                amount = round(total_amount - monthly_amount * (months - 1), 2)
            else:
                amount = monthly_amount

            entry = AmortizationEntry(
                amortization_id=amort.id,
                period=period,
                amount=amount,
                is_posted=False,
            )
            self.db.add(entry)
            await self.db.flush()

            await self._post_entry(entry, amort)

        amort.status = "completed"
        return amort

    async def _lookup_category(self, management_name: str) -> dict | None:
        """Look up grouping/class from category tree by management name."""
        result = await self.db.execute(
            select(CategoryNode).where(CategoryNode.level == 3, CategoryNode.name == management_name)
        )
        node = result.scalar_one_or_none()
        if not node:
            return None
        class_node = None
        grouping_node = None
        if node.parent_id:
            result = await self.db.execute(select(CategoryNode).where(CategoryNode.id == node.parent_id))
            class_node = result.scalar_one_or_none()
        if class_node and class_node.parent_id:
            result = await self.db.execute(select(CategoryNode).where(CategoryNode.id == class_node.parent_id))
            grouping_node = result.scalar_one_or_none()
        return {
            "management": node.name,
            "class_name": class_node.name if class_node else None,
            "grouping": grouping_node.name if grouping_node else None,
        }

    async def _ensure_category_node(
        self, grouping: str, class_name: str, management: str,
        cf_line: str | None = None,
    ) -> None:
        """确保 Grouping→Class→Management 这条三层路径存在于分类树。

        L3 在本系统中按名称唯一（lookup 只按 name 匹配），所以已存在的 L3 直接复用，
        不会重复创建，也不会改动其挂载位置。
        """
        if not (grouping and class_name and management):
            return
        l1 = await self._find_or_create_node(grouping, 1, None)
        l2 = await self._find_or_create_node(class_name, 2, l1.id)
        # L3 按名称全局查找，避免在不同父节点下产生重名重复
        existing = await self.db.execute(
            select(CategoryNode).where(CategoryNode.level == 3, CategoryNode.name == management)
        )
        if existing.scalar_one_or_none():
            return
        node = CategoryNode(name=management, level=3, parent_id=l2.id, cf_line=cf_line)
        self.db.add(node)
        await self.db.flush()

    async def _find_or_create_node(
        self, name: str, level: int, parent_id: int | None,
        cf_line: str | None = None,
    ) -> CategoryNode:
        q = select(CategoryNode).where(
            CategoryNode.level == level, CategoryNode.name == name
        )
        q = q.where(CategoryNode.parent_id.is_(None) if parent_id is None
                    else CategoryNode.parent_id == parent_id)
        node = (await self.db.execute(q)).scalar_one_or_none()
        if node:
            return node
        node = CategoryNode(name=name, level=level, parent_id=parent_id, cf_line=cf_line)
        self.db.add(node)
        await self.db.flush()
        return node

    async def _post_entry(self, entry: AmortizationEntry, amort: Amortization) -> None:
        """Create a pair of ADJ transactions (debit expense, credit prepaid)."""
        abstract_text = f"摊销: {amort.expense_account} ({entry.period.strftime('%Y-%m')})"

        # Debit: expense side (negative cf = cash outflow / expense recognition)
        debit_txn = Transaction(
            entity=amort.entity,
            account="ADJ",
            counterpart="摊销分录",
            period=entry.period,
            abstract=abstract_text,
            ccy="CNY",
            cf=-entry.amount,
            exchange_rate=1.0,
            cf_in_cny=-entry.amount,
            management=amort.expense_account,
            grouping=amort.grouping,
            class_name=amort.class_name,
            classification_method="amortization",
            classification_confidence=1.0,
            import_batch="amortization",
        )
        self.db.add(debit_txn)
        await self.db.flush()

        # Credit: prepaid side (positive cf = reduction of prepaid asset)
        credit_txn = Transaction(
            entity=amort.entity,
            account="ADJ",
            counterpart="摊销分录",
            period=entry.period,
            abstract=abstract_text,
            ccy="CNY",
            cf=entry.amount,
            exchange_rate=1.0,
            cf_in_cny=entry.amount,
            management=amort.prepaid_account,
            grouping="98_非损益",
            class_name="98_非损益",
            classification_method="amortization",
            classification_confidence=1.0,
            import_batch="amortization",
        )
        self.db.add(credit_txn)
        await self.db.flush()

        entry.debit_transaction_id = debit_txn.id
        entry.credit_transaction_id = credit_txn.id
        entry.is_posted = True

    async def list_amortizations(self) -> list[dict]:
        """List all amortizations with posted_count and total_entries."""
        result = await self.db.execute(
            select(Amortization).order_by(Amortization.created_at.desc())
        )
        amorts = list(result.scalars().all())

        items = []
        for a in amorts:
            counts = await self.db.execute(
                select(
                    func.count(AmortizationEntry.id).label("total"),
                    func.count(AmortizationEntry.id).filter(AmortizationEntry.is_posted.is_(True)).label("posted"),
                ).where(AmortizationEntry.amortization_id == a.id)
            )
            row = counts.one()
            items.append({
                "amortization": a,
                "total_entries": row.total,
                "posted_count": row.posted,
            })
        return items

    async def get_amortization_detail(self, amort_id: int) -> dict | None:
        """Get a single amortization with its entries."""
        result = await self.db.execute(
            select(Amortization).where(Amortization.id == amort_id)
        )
        amort = result.scalar_one_or_none()
        if not amort:
            return None

        entries_result = await self.db.execute(
            select(AmortizationEntry)
            .where(AmortizationEntry.amortization_id == amort_id)
            .order_by(AmortizationEntry.period)
        )
        entries = list(entries_result.scalars().all())

        posted_count = sum(1 for e in entries if e.is_posted)

        return {
            "amortization": amort,
            "entries": entries,
            "total_entries": len(entries),
            "posted_count": posted_count,
        }

    async def delete_amortization(self, amort_id: int) -> bool:
        """Delete amortization and its related ADJ transactions."""
        result = await self.db.execute(
            select(Amortization).where(Amortization.id == amort_id)
        )
        amort = result.scalar_one_or_none()
        if not amort:
            return False

        # Get all entries to find transaction IDs
        entries_result = await self.db.execute(
            select(AmortizationEntry).where(AmortizationEntry.amortization_id == amort_id)
        )
        entries = list(entries_result.scalars().all())

        # Collect transaction IDs to delete
        txn_ids = []
        for entry in entries:
            if entry.debit_transaction_id:
                txn_ids.append(entry.debit_transaction_id)
            if entry.credit_transaction_id:
                txn_ids.append(entry.credit_transaction_id)

        # Delete entries
        for entry in entries:
            await self.db.delete(entry)

        # Delete related transactions
        if txn_ids:
            txn_result = await self.db.execute(
                select(Transaction).where(Transaction.id.in_(txn_ids))
            )
            for txn in txn_result.scalars().all():
                await self.db.delete(txn)

        # Delete the amortization record
        await self.db.delete(amort)
        return True
