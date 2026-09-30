"""FS for Investor — line-item definitions for Profit & Loss and Cash Flow statements."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FSLine:
    """One row in the financial statement."""
    key: str
    label: str
    indent: int = 0
    style: str = "item"  # "header" | "item" | "subtotal" | "total"
    # Data source: which DB field & values to sum
    source_field: Optional[str] = None          # "grouping" | "management" | "cf_line" | None
    source_values: list[str] = field(default_factory=list)
    exclude_management: list[str] = field(default_factory=list)
    include_management: list[str] = field(default_factory=list)
    # For special source: import_batch filter
    source_import_batch: Optional[str] = None
    source_cf_negative: bool = False            # only negative cf_in_cny
    # Formula: reference other keys (addition)
    formula_add: list[str] = field(default_factory=list)
    formula_sub: list[str] = field(default_factory=list)
    # Fixed value (always 0)
    fixed_zero: bool = False
    # Drilldown hint for frontend
    drilldown_field: Optional[str] = None       # "grouping" | "management" | "cf_line"
    drilldown_value: Optional[str] = None


# ──────────────────────────────────────────────
# Profit & Loss (利润表)
# ──────────────────────────────────────────────
PROFIT_LOSS_LINES: list[FSLine] = [
    FSLine(
        key="revenue", label="营业收入", style="item",
        source_field="grouping", source_values=["01_营业收入"],
        drilldown_field="grouping", drilldown_value="01_营业收入",
    ),
    FSLine(key="cogs", label="减：营业成本", style="item", fixed_zero=True),
    FSLine(
        key="tax_surcharge", label="税金及附加", style="item",
        source_field="grouping", source_values=["07_缴纳税金"],
        exclude_management=["企业所得税"],
        drilldown_field="grouping", drilldown_value="07_缴纳税金",
    ),
    FSLine(key="selling_expense", label="销售费用", style="item", fixed_zero=True),
    # 管理费用 = 人工 + 折旧 + 其他
    FSLine(
        key="admin_expense", label="管理费用", style="subtotal",
        formula_add=["admin_labor", "admin_depreciation", "admin_other"],
    ),
    FSLine(
        key="admin_labor", label="其中：人工", indent=1, style="item",
        source_field="grouping",
        source_values=["02_经常性人工成本", "04_兼职顾问"],
        drilldown_field="grouping", drilldown_value="02_经常性人工成本",
    ),
    FSLine(
        key="admin_depreciation", label="折旧摊销", indent=1, style="item",
        source_import_batch="amortization", source_cf_negative=True,
    ),
    FSLine(
        key="admin_other", label="其他", indent=1, style="item",
        source_field="grouping",
        source_values=[
            "06_通信/云服务/软件",
            "08_房租/物业/水电",
            "09_市场营销",
            "10_人才法服务",
            "13_差旅费报销及其他办公杂费",
        ],
    ),
    FSLine(
        key="finance_expense", label="财务费用", style="item",
        source_field="grouping", source_values=["11_各类手续费/结售汇费用"],
        include_management=["利息收入"],
        drilldown_field="grouping", drilldown_value="11_各类手续费/结售汇费用",
    ),
    FSLine(
        key="other_income", label="加：其他收益", style="item",
        source_field="management",
        source_values=["政府补助", "税收返还", "就业服务奖励"],
    ),
    # 营业利润 = 收入 + 成本 + 税金附加 + 销售费用 + 管理费用 + 财务费用 + 其他收益
    # (all expenses are already negative in DB, so we ADD them)
    FSLine(
        key="operating_profit", label="营业利润", style="total",
        formula_add=["revenue", "cogs", "tax_surcharge", "selling_expense",
                     "admin_expense", "finance_expense", "other_income"],
    ),
    FSLine(key="non_op_income", label="加：营业外收入", style="item", fixed_zero=True),
    FSLine(key="non_op_expense", label="减：营业外支出", style="item", fixed_zero=True),
    # 利润总额 = 营业利润 + 营业外收入 + 营业外支出 (支出已为负)
    FSLine(
        key="profit_before_tax", label="利润总额", style="total",
        formula_add=["operating_profit", "non_op_income", "non_op_expense"],
    ),
    FSLine(
        key="income_tax", label="减：所得税费用", style="item",
        source_field="management", source_values=["企业所得税"],
        drilldown_field="management", drilldown_value="企业所得税",
    ),
    # 净利润 = 利润总额 + 所得税 (所得税已为负)
    FSLine(
        key="net_profit", label="净利润", style="total",
        formula_add=["profit_before_tax", "income_tax"],
    ),
    # EBITDA = 利润总额 - 折旧摊销 (折旧摊销是负值,所以减去负值=加)
    FSLine(
        key="ebitda", label="EBITDA", style="total",
        formula_add=["profit_before_tax"],
        formula_sub=["admin_depreciation"],
    ),
]


# ──────────────────────────────────────────────
# Cash Flow Statement (现金流量表)
# ──────────────────────────────────────────────
CASH_FLOW_LINES: list[FSLine] = [
    FSLine(key="cf_header_op", label="一、经营活动产生的现金流量", style="header"),
    FSLine(
        key="cf_op_sales", label="销售产成品、商品、提供劳务收到的现金", indent=1, style="item",
        source_field="cf_line", source_values=["销售产成品、商品、提供劳务收到的现金"],
        drilldown_field="cf_line", drilldown_value="销售产成品、商品、提供劳务收到的现金",
    ),
    FSLine(
        key="cf_op_tax_refund", label="收到的税费返还", indent=1, style="item",
        source_field="cf_line", source_values=["收到的税费返还"],
        drilldown_field="cf_line", drilldown_value="收到的税费返还",
    ),
    FSLine(
        key="cf_op_other_in", label="收到其他与经营活动有关的现金", indent=1, style="item",
        source_field="cf_line", source_values=["收到其他与经营活动有关的现金"],
        drilldown_field="cf_line", drilldown_value="收到其他与经营活动有关的现金",
    ),
    FSLine(
        key="cf_op_inflow", label="经营活动现金流入小计", style="subtotal",
        formula_add=["cf_op_sales", "cf_op_tax_refund", "cf_op_other_in"],
    ),
    FSLine(
        key="cf_op_payroll", label="支付给职工以及为职工支付的现金", indent=1, style="item",
        source_field="cf_line", source_values=["支付给职工以及为职工支付的现金"],
        drilldown_field="cf_line", drilldown_value="支付给职工以及为职工支付的现金",
    ),
    FSLine(
        key="cf_op_tax_paid", label="支付的各项税费", indent=1, style="item",
        source_field="cf_line", source_values=["支付的各项税费"],
        drilldown_field="cf_line", drilldown_value="支付的各项税费",
    ),
    FSLine(
        key="cf_op_other_out", label="支付其他与经营活动有关的现金", indent=1, style="item",
        source_field="cf_line", source_values=["支付其他与经营活动有关的现金"],
        drilldown_field="cf_line", drilldown_value="支付其他与经营活动有关的现金",
    ),
    FSLine(
        key="cf_op_outflow", label="经营活动现金流出小计", style="subtotal",
        formula_add=["cf_op_payroll", "cf_op_tax_paid", "cf_op_other_out"],
    ),
    FSLine(
        key="cf_op_net", label="经营活动产生的现金流量净额", style="total",
        formula_add=["cf_op_inflow", "cf_op_outflow"],
    ),
    # 投资活动
    FSLine(key="cf_header_inv", label="二、投资活动产生的现金流量", style="header"),
    FSLine(
        key="cf_inv_fixed", label="购建固定资产、无形资产和其他长期资产支付的现金", indent=1, style="item",
        source_field="cf_line", source_values=["购建固定资产支付的现金"],
        drilldown_field="cf_line", drilldown_value="购建固定资产支付的现金",
    ),
    FSLine(
        key="cf_inv_net", label="投资活动产生的现金流量净额", style="total",
        formula_add=["cf_inv_fixed"],
    ),
    # 筹资活动
    FSLine(key="cf_header_fin", label="三、筹资活动产生的现金流量", style="header"),
    FSLine(
        key="cf_fin_invest", label="吸收投资收到的现金", indent=1, style="item",
        source_field="cf_line", source_values=["吸收投资收到的现金"],
        drilldown_field="cf_line", drilldown_value="吸收投资收到的现金",
    ),
    FSLine(
        key="cf_fin_net", label="筹资活动产生的现金流量净额", style="total",
        formula_add=["cf_fin_invest"],
    ),
    # 汇率变动
    FSLine(key="cf_fx", label="四、汇率变动对现金及现金等价物的影响", style="total"),
    # 现金净增加额
    FSLine(
        key="cf_net_increase", label="五、现金及现金等价物净增加额", style="total",
        formula_add=["cf_op_net", "cf_inv_net", "cf_fin_net", "cf_fx"],
    ),
    FSLine(key="cf_opening_bal", label="加：期初现金及现金等价物余额", style="item"),
    FSLine(
        key="cf_closing_bal", label="六、期末现金及现金等价物余额", style="total",
        formula_add=["cf_net_increase", "cf_opening_bal"],
    ),
]

# All known cf_line values used above (for computing the FX residual)
MAPPED_CF_LINES = set()
for _line in CASH_FLOW_LINES:
    if _line.source_field == "cf_line":
        MAPPED_CF_LINES.update(_line.source_values)
