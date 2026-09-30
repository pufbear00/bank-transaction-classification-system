import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Select, Space, Button, message } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import {
  getMonthlySummary,
  exportMonthlySummary,
  listBankAccounts,
  type MonthlySummaryResponse,
} from "../../api/client";

const MONTH_LABELS: Record<string, string> = {
  "01": "1月", "02": "2月", "03": "3月", "04": "4月",
  "05": "5月", "06": "6月", "07": "7月", "08": "8月",
  "09": "9月", "10": "10月", "11": "11月", "12": "12月",
};

const fmt = (v: number, hasData = true) => {
  if (!hasData) return "-";
  if (v === 0) return "0";
  return v.toLocaleString("zh-CN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

/** Get the last day of a month string like "2026-01" */
function lastDayOfMonth(monthStr: string): string {
  const [y, m] = monthStr.split("-").map(Number);
  const d = new Date(y, m, 0); // day 0 of next month = last day of this month
  return `${y}-${String(m).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function MonthlyReportPage() {
  const navigate = useNavigate();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [entity, setEntity] = useState<string>();
  const [entities, setEntities] = useState<string[]>([]);
  const [data, setData] = useState<MonthlySummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listBankAccounts().then((accts) => {
      setEntities([...new Set(accts.map((a) => a.entity))]);
    });
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { year };
      if (entity) params.entity = entity;
      const res = await getMonthlySummary(params);
      setData(res);
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [year, entity]);

  const handleExport = async () => {
    try {
      const params: Record<string, unknown> = { year };
      if (entity) params.entity = entity;
      const blob = await exportMonthlySummary(params);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `management_report_${year}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error("导出失败");
    }
  };

  const months = data?.months || [];

  // Build flat rows for the table
  // drilldown stores the filter info for navigating to transaction list
  type DrillDown = {
    management?: string;
    grouping?: string;     // DB grouping = L2 class in report
    class_name?: string;   // DB class_name = L1 grouping in report
    unclassified?: boolean;
  };

  type Row = {
    key: string;
    label: string;
    level: "grouping" | "class" | "management" | "grand" | "pnl" | "unclassified";
    months: Record<string, number>;
    activeMonths: string[];
    total: number;
    drilldown?: DrillDown;
  };

  const rows: Row[] = useMemo(() => {
    if (!data) return [];
    const result: Row[] = [];

    for (const section of data.sections) {
      result.push({
        key: `g-${section.name}`,
        label: section.name,
        level: "grouping",
        months: section.months,
        activeMonths: section.active_months,
        total: section.total,
        drilldown: { class_name: section.name },
      });
      for (const cls of section.classes) {
        // Only show class row if there are multiple classes in the grouping
        if (section.classes.length > 1) {
          result.push({
            key: `c-${section.name}-${cls.name}`,
            label: cls.name,
            level: "class",
            months: cls.months,
            activeMonths: cls.active_months,
            total: cls.total,
            drilldown: { grouping: cls.name },
          });
        }
        for (const item of cls.items) {
          result.push({
            key: `m-${section.name}-${cls.name}-${item.name}`,
            label: item.name,
            level: "management",
            months: item.months,
            activeMonths: item.active_months,
            total: item.total,
            drilldown: { management: item.name },
          });
        }
      }
    }

    // Unclassified
    if (data.unclassified.total !== 0) {
      result.push({
        key: "unclassified",
        label: "未分类",
        level: "unclassified",
        months: data.unclassified.months,
        activeMonths: data.unclassified.active_months,
        total: data.unclassified.total,
        drilldown: { unclassified: true },
      });
    }

    // Grand total
    result.push({
      key: "grand-total",
      label: "总计",
      level: "grand",
      months: data.grand_total.months,
      activeMonths: data.grand_total.active_months,
      total: data.grand_total.total,
      // no drilldown for grand total
    });

    // P&L total (excludes 98_非损益 / 99_内部往来) — 让摊销费用在 6-12 月体现
    if (data.pnl_total) {
      result.push({
        key: "pnl-total",
        label: "损益合计（不含非损益）",
        level: "pnl",
        months: data.pnl_total.months,
        activeMonths: data.pnl_total.active_months,
        total: data.pnl_total.total,
      });
    }

    return result;
  }, [data]);

  /** Navigate to transaction list with filters */
  const handleDrillDown = (drilldown: DrillDown, monthStr?: string) => {
    const params = new URLSearchParams();
    if (drilldown.management) params.set("management", drilldown.management);
    if (drilldown.grouping) params.set("grouping", drilldown.grouping);
    if (drilldown.class_name) params.set("class_name", drilldown.class_name);
    if (drilldown.unclassified) params.set("unclassified", "true");
    if (entity) params.set("entity", entity);

    if (monthStr) {
      // Specific month: first day to last day
      params.set("start_date", `${monthStr}-01`);
      params.set("end_date", lastDayOfMonth(monthStr));
    } else {
      // Full year
      params.set("start_date", `${year}-01-01`);
      params.set("end_date", `${year}-12-31`);
    }

    navigate(`/transactions?${params.toString()}`);
  };

  const rowStyle = (level: Row["level"]): React.CSSProperties => {
    switch (level) {
      case "grouping":
        return { background: "#e2efda", fontWeight: 700, fontSize: 13 };
      case "class":
        return { background: "#f2f2f2", fontWeight: 600 };
      case "management":
        return { paddingLeft: 24 };
      case "grand":
        return { background: "#d9e1f2", fontWeight: 700, fontSize: 14, borderTop: "2px solid #999" };
      case "pnl":
        return { background: "#fff7cc", fontWeight: 700, fontSize: 14, borderBottom: "2px solid #999" };
      case "unclassified":
        return { background: "#fff2e8", fontWeight: 600 };
      default:
        return {};
    }
  };

  const cellColor = (v: number) => {
    if (v === 0) return "#ccc";
    return v > 0 ? "#389e0d" : "#cf1322";
  };

  const clickableStyle: React.CSSProperties = {
    cursor: "pointer",
    transition: "background 0.15s",
  };

  return (
    <Card
      title="月度汇总报表 (Management)"
      loading={loading}
      extra={
        <Space>
          <Select
            value={year}
            onChange={setYear}
            style={{ width: 100 }}
            options={Array.from({ length: 5 }, (_, i) => currentYear - i).map((y) => ({
              value: y,
              label: `${y}年`,
            }))}
          />
          <Select
            placeholder="全部实体"
            allowClear
            style={{ width: 140 }}
            value={entity}
            onChange={setEntity}
            options={entities.map((e) => ({ value: e, label: e }))}
          />
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出 XLSX
          </Button>
        </Space>
      }
    >
      <style>{`
        .report-cell-clickable:hover {
          background: rgba(24, 144, 255, 0.08) !important;
          text-decoration: underline;
        }
      `}</style>
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 12,
            fontFamily: "system-ui, -apple-system, sans-serif",
          }}
        >
          <thead>
            <tr style={{ background: "#d9e1f2", fontWeight: 700, textAlign: "center" }}>
              <th
                style={{
                  textAlign: "left",
                  padding: "8px 12px",
                  borderBottom: "2px solid #aaa",
                  minWidth: 220,
                  position: "sticky",
                  left: 0,
                  background: "#d9e1f2",
                  zIndex: 1,
                }}
              >
                求和项: CF in CNY
              </th>
              {months.map((m) => (
                <th
                  key={m}
                  style={{
                    padding: "8px 8px",
                    borderBottom: "2px solid #aaa",
                    minWidth: 110,
                    whiteSpace: "nowrap",
                  }}
                >
                  {MONTH_LABELS[m.slice(5)] || m}
                </th>
              ))}
              <th
                style={{
                  padding: "8px 8px",
                  borderBottom: "2px solid #aaa",
                  minWidth: 120,
                  fontWeight: 800,
                }}
              >
                总计
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const style = rowStyle(row.level);
              const isManagement = row.level === "management";
              const canDrill = !!row.drilldown;
              return (
                <tr key={row.key} style={style}>
                  <td
                    className={canDrill ? "report-cell-clickable" : undefined}
                    style={{
                      padding: isManagement ? "4px 12px 4px 36px" : "6px 12px",
                      borderBottom: "1px solid #eee",
                      whiteSpace: "nowrap",
                      position: "sticky",
                      left: 0,
                      background: style.background || "#fff",
                      zIndex: 1,
                      ...(canDrill ? clickableStyle : {}),
                    }}
                    onClick={canDrill ? () => handleDrillDown(row.drilldown!) : undefined}
                    title={canDrill ? "点击查看对应流水明细" : undefined}
                  >
                    {row.label}
                  </td>
                  {months.map((m) => {
                    const val = row.months[m] ?? 0;
                    const hasData = row.activeMonths.includes(m);
                    const canDrillMonth = canDrill && hasData;
                    return (
                      <td
                        key={m}
                        className={canDrillMonth ? "report-cell-clickable" : undefined}
                        style={{
                          padding: "4px 8px",
                          borderBottom: "1px solid #eee",
                          textAlign: "right",
                          fontVariantNumeric: "tabular-nums",
                          color: cellColor(val),
                          ...(canDrillMonth ? clickableStyle : {}),
                        }}
                        onClick={canDrillMonth ? () => handleDrillDown(row.drilldown!, m) : undefined}
                        title={canDrillMonth ? "点击查看该月流水明细" : undefined}
                      >
                        {fmt(val, hasData)}
                      </td>
                    );
                  })}
                  <td
                    className={canDrill && row.total !== 0 ? "report-cell-clickable" : undefined}
                    style={{
                      padding: "4px 8px",
                      borderBottom: "1px solid #eee",
                      textAlign: "right",
                      fontWeight: 700,
                      fontVariantNumeric: "tabular-nums",
                      color: cellColor(row.total),
                      ...(canDrill && row.total !== 0 ? clickableStyle : {}),
                    }}
                    onClick={canDrill && row.total !== 0 ? () => handleDrillDown(row.drilldown!) : undefined}
                    title={canDrill && row.total !== 0 ? "点击查看全年流水明细" : undefined}
                  >
                    {fmt(row.total)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
