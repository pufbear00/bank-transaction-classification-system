import { useState, useEffect, useMemo } from "react";
import { Card, Select, InputNumber, message, Spin } from "antd";
import { getCashBalanceYearly, updateTransaction } from "../../api/client";
import type { CashBalanceYearlyResponse } from "../../types";

const currentYear = new Date().getFullYear();
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i).map(
  (y) => ({ label: String(y), value: y })
);

const MONTH_LABELS = [
  "1月", "2月", "3月", "4月", "5月", "6月",
  "7月", "8月", "9月", "10月", "11月", "12月",
];

const fmt = (v: number | null | undefined) => {
  if (v === null || v === undefined || v === 0) return "-";
  return v.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

/** Parse "2026-03-25" → "3.25" */
const dateSuffix = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}.${d.getDate()}`;
};

export default function CashBalancePage() {
  const [year, setYear] = useState(currentYear);
  const [data, setData] = useState<CashBalanceYearlyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [burnRate, setBurnRate] = useState<number | null>(null);
  const [runway, setRunway] = useState<number | null>(null);
  const [editingCell, setEditingCell] = useState<{ accountId: number; monthKey: string } | null>(null);
  const [editValue, setEditValue] = useState<number | null>(null);

  const fetchData = async (y: number) => {
    setLoading(true);
    try {
      const res = await getCashBalanceYearly({ year: y });
      setData(res);
    } catch (err: any) {
      const detail = err?.response?.status
        ? `HTTP ${err.response.status}: ${err.response.statusText}`
        : err?.message || "未知错误";
      message.error(`加载失败: ${detail}`);
      console.error("cash-balance-yearly error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(year);
    setBurnRate(null);
    setRunway(null);
  }, [year]);

  // All 12 months for display
  const allMonths = useMemo(
    () => Array.from({ length: 12 }, (_, i) => `${year}-${String(i + 1).padStart(2, "0")}`),
    [year]
  );

  // Latest total CNY for burn rate / runway calculation
  const latestTotalCny = data?.total_cny_latest ?? 0;

  const handleCellClick = (accountId: number, monthKey: string, balance: number) => {
    setEditingCell({ accountId, monthKey });
    setEditValue(balance);
  };

  const handleCellSave = async (transactionId: number) => {
    if (editValue === null) {
      setEditingCell(null);
      return;
    }
    try {
      await updateTransaction(transactionId, { bal: editValue });
      message.success("余额已更新");
      setEditingCell(null);
      fetchData(year);
    } catch {
      message.error("更新失败");
    }
  };

  const handleBurnRateChange = (val: number | null) => {
    setBurnRate(val);
    if (val && val !== 0 && latestTotalCny) {
      setRunway(Math.round((latestTotalCny / val) * 100) / 100);
    } else {
      setRunway(null);
    }
  };

  const handleRunwayChange = (val: number | null) => {
    setRunway(val);
    if (val && val !== 0 && latestTotalCny) {
      setBurnRate(Math.round((latestTotalCny / val) * 100) / 100);
    } else {
      setBurnRate(null);
    }
  };

  const stickyLeft = (left: number, zIndex = 2): React.CSSProperties => ({
    position: "sticky",
    left,
    zIndex,
    background: "inherit",
  });

  const thBase: React.CSSProperties = {
    padding: "8px 10px",
    borderBottom: "2px solid #aaa",
    whiteSpace: "nowrap",
    textAlign: "center",
    fontSize: 12,
  };

  const tdBase: React.CSSProperties = {
    padding: "6px 10px",
    borderBottom: "1px solid #eee",
    textAlign: "right",
    fontVariantNumeric: "tabular-nums",
    fontSize: 12,
    whiteSpace: "nowrap",
  };

  const colWidths = { entity: 100, account: 120, ccy: 50 };

  return (
    <Card
      title="现金余额总览"
      extra={
        <Select
          value={year}
          onChange={setYear}
          options={yearOptions}
          style={{ width: 100 }}
        />
      }
    >
      <Spin spinning={loading}>
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              borderCollapse: "collapse",
              fontFamily: "system-ui, -apple-system, sans-serif",
              minWidth: "100%",
            }}
          >
            <thead>
              <tr style={{ background: "#d9e1f2", fontWeight: 700 }}>
                <th
                  style={{
                    ...thBase,
                    textAlign: "left",
                    minWidth: colWidths.entity,
                    ...stickyLeft(0, 3),
                    background: "#d9e1f2",
                  }}
                >
                  实体
                </th>
                <th
                  style={{
                    ...thBase,
                    textAlign: "left",
                    minWidth: colWidths.account,
                    ...stickyLeft(colWidths.entity, 3),
                    background: "#d9e1f2",
                  }}
                >
                  账户
                </th>
                <th
                  style={{
                    ...thBase,
                    minWidth: colWidths.ccy,
                    ...stickyLeft(colWidths.entity + colWidths.account, 3),
                    background: "#d9e1f2",
                  }}
                >
                  币种
                </th>
                {allMonths.map((_, i) => (
                  <th key={i} style={{ ...thBase, minWidth: 110 }}>
                    {MONTH_LABELS[i]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data?.accounts.map((acct) => (
                <tr key={acct.account_id} style={{ background: "#fff" }}>
                  <td
                    style={{
                      ...tdBase,
                      textAlign: "left",
                      fontWeight: 500,
                      ...stickyLeft(0),
                    }}
                  >
                    {acct.entity}
                  </td>
                  <td
                    style={{
                      ...tdBase,
                      textAlign: "left",
                      ...stickyLeft(colWidths.entity),
                    }}
                  >
                    {acct.account}
                  </td>
                  <td
                    style={{
                      ...tdBase,
                      textAlign: "center",
                      ...stickyLeft(colWidths.entity + colWidths.account),
                    }}
                  >
                    {acct.ccy}
                  </td>
                  {allMonths.map((monthKey) => {
                    const mb = acct.balances[monthKey];
                    if (!mb) {
                      return (
                        <td key={monthKey} style={{ ...tdBase, color: "#ccc" }}>
                          -
                        </td>
                      );
                    }
                    const isEditing =
                      editingCell?.accountId === acct.account_id &&
                      editingCell?.monthKey === monthKey;
                    return (
                      <td key={monthKey} style={tdBase}>
                        {isEditing ? (
                          <InputNumber
                            size="small"
                            value={editValue}
                            onChange={setEditValue}
                            onPressEnter={() => handleCellSave(mb.transaction_id)}
                            onBlur={() => handleCellSave(mb.transaction_id)}
                            autoFocus
                            style={{ width: 110 }}
                            controls={false}
                          />
                        ) : (
                          <div
                            onClick={() => handleCellClick(acct.account_id, monthKey, mb.balance)}
                            style={{ cursor: "pointer" }}
                            title="点击编辑余额"
                          >
                            {fmt(mb.balance)}
                          </div>
                        )}
                        {acct.ccy !== "CNY" && (
                          <div style={{ color: "#888", fontSize: 10, lineHeight: 1.2 }}>
                            ¥{fmt(mb.balance_cny)}
                          </div>
                        )}
                        {!mb.is_month_end && (
                          <div style={{ color: "#999", fontSize: 10, lineHeight: 1 }}>
                            ({dateSuffix(mb.balance_date)})
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}

              {/* 合计行 */}
              <tr
                style={{
                  background: "#e2efda",
                  fontWeight: 700,
                  fontSize: 13,
                }}
              >
                <td
                  colSpan={3}
                  style={{
                    padding: "8px 10px",
                    borderTop: "2px solid #999",
                    borderBottom: "1px solid #ccc",
                    ...stickyLeft(0),
                    background: "#e2efda",
                  }}
                >
                  合计 (CNY)
                </td>
                {allMonths.map((monthKey) => {
                  const val = data?.monthly_totals_cny[monthKey];
                  return (
                    <td
                      key={monthKey}
                      style={{
                        padding: "8px 10px",
                        borderTop: "2px solid #999",
                        borderBottom: "1px solid #ccc",
                        textAlign: "right",
                        fontVariantNumeric: "tabular-nums",
                        fontSize: 12,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {fmt(val)}
                    </td>
                  );
                })}
              </tr>

              {/* 现金流动行 */}
              <tr
                style={{
                  background: "#fce4ec",
                  fontWeight: 700,
                  fontSize: 13,
                }}
              >
                <td
                  colSpan={3}
                  style={{
                    padding: "8px 10px",
                    borderBottom: "1px solid #ccc",
                    ...stickyLeft(0),
                    background: "#fce4ec",
                  }}
                >
                  现金流动 (CNY)
                </td>
                {allMonths.map((monthKey, i) => {
                  const cur = data?.monthly_totals_cny[monthKey];
                  const prevKey = allMonths[i - 1];
                  const prev = prevKey ? data?.monthly_totals_cny[prevKey] : undefined;
                  const flow = cur != null && prev != null ? cur - prev : undefined;
                  return (
                    <td
                      key={monthKey}
                      style={{
                        padding: "8px 10px",
                        borderBottom: "1px solid #ccc",
                        textAlign: "right",
                        fontVariantNumeric: "tabular-nums",
                        fontSize: 12,
                        whiteSpace: "nowrap",
                        color: flow != null ? (flow >= 0 ? "#389e0d" : "#cf1322") : undefined,
                      }}
                    >
                      {flow != null
                        ? `${flow >= 0 ? "+" : ""}${flow.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : "-"}
                    </td>
                  );
                })}
              </tr>

              {/* Burn Rate */}
              <tr style={{ background: "#fff7e6" }}>
                <td
                  colSpan={3}
                  style={{
                    padding: "6px 10px",
                    borderBottom: "1px solid #eee",
                    fontWeight: 600,
                    fontSize: 12,
                    ...stickyLeft(0),
                    background: "#fff7e6",
                  }}
                >
                  Burn Rate (月均消耗 CNY)
                </td>
                <td
                  colSpan={12}
                  style={{
                    padding: "2px 10px",
                    borderBottom: "1px solid #eee",
                  }}
                >
                  <InputNumber
                    value={burnRate}
                    onChange={handleBurnRateChange}
                    formatter={(v) =>
                      v != null && String(v) !== ""
                        ? Number(v).toLocaleString("zh-CN", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })
                        : ""
                    }
                    parser={(v) =>
                      Number(String(v || "").replace(/,/g, "")) as 0
                    }
                    style={{ width: 200 }}
                    size="small"
                    controls={false}
                    placeholder="输入月均消耗"
                  />
                </td>
              </tr>

              {/* Runway */}
              <tr style={{ background: "#fff7e6" }}>
                <td
                  colSpan={3}
                  style={{
                    padding: "6px 10px",
                    borderBottom: "1px solid #eee",
                    fontWeight: 600,
                    fontSize: 12,
                    ...stickyLeft(0),
                    background: "#fff7e6",
                  }}
                >
                  Runway (月数)
                </td>
                <td
                  colSpan={12}
                  style={{
                    padding: "2px 10px",
                    borderBottom: "1px solid #eee",
                  }}
                >
                  <InputNumber
                    value={runway}
                    onChange={handleRunwayChange}
                    formatter={(v) =>
                      v != null && String(v) !== ""
                        ? Number(v).toLocaleString("zh-CN", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })
                        : ""
                    }
                    parser={(v) =>
                      Number(String(v || "").replace(/,/g, "")) as 0
                    }
                    style={{ width: 200 }}
                    size="small"
                    controls={false}
                    placeholder="输入月数"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Spin>
    </Card>
  );
}
