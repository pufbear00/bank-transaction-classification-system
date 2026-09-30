import { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Card,
  Table,
  Input,
  Select,
  AutoComplete,
  DatePicker,
  InputNumber,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Cascader,
  message,
  Tooltip,
  Row,
  Col,
} from "antd";
import {
  SearchOutlined,
  DownloadOutlined,
  EditOutlined,
  CheckOutlined,
  ThunderboltOutlined,
  DollarOutlined,
  DeleteOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { Resizable } from "react-resizable";
import "react-resizable/css/styles.css";
import dayjs from "dayjs";
import type { Transaction, CategoryNode, BankAccount } from "../../types";

const ResizableTitle = (props: any) => {
  const { onResize, width, ...restProps } = props;
  if (!width) return <th {...restProps} />;
  return (
    <Resizable
      width={width}
      height={0}
      handle={
        <span
          className="react-resizable-handle"
          style={{ position: "absolute", right: -5, bottom: 0, top: 0, width: 10, cursor: "col-resize", zIndex: 1 }}
          onClick={(e) => e.stopPropagation()}
        />
      }
      onResize={onResize}
      draggableOpts={{ enableUserSelectHack: false }}
    >
      <th {...restProps} />
    </Resizable>
  );
};
import {
  listTransactions,
  createTransaction,
  updateTransaction,
  bulkUpdateTransactions,
  bulkDeleteTransactions,
  exportTransactions,
  reclassifyTransactions,
  fixExchangeRates,
  getCategoryTree,
  getCategoriesFlat,
  listBankAccounts,
  lookupCategory,
} from "../../api/client";

const { RangePicker } = DatePicker;

function parseSearchParams(search: string) {
  const p = new URLSearchParams(search);
  if (!p.toString()) return null;
  return {
    entity: p.get("entity") || undefined,
    account: p.get("account") || undefined,
    management: p.get("management") || undefined,
    grouping: p.get("grouping") || undefined,
    class_name: p.get("class_name") || undefined,
    cf_line: p.get("cf_line") || undefined,
    unclassified: p.get("unclassified") === "true",
    dateRange: p.get("start_date") && p.get("end_date")
      ? [p.get("start_date")!, p.get("end_date")!] as [string, string]
      : null,
  };
}

export default function TransactionListPage() {
  // useLocation is stable across StrictMode remounts (reads from React Router state, not window.location)
  const location = useLocation();
  const nav = useNavigate();
  const [initParams] = useState(() => parseSearchParams(location.search));

  // Clear URL query string after reading (in effect, safe for StrictMode)
  useEffect(() => {
    if (location.search) {
      nav(location.pathname, { replace: true });
    }
  }, []);

  const [data, setData] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [sumCf, setSumCf] = useState(0);
  const [sumCfInCny, setSumCfInCny] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sortBy, setSortBy] = useState("period");
  const [sortOrder, setSortOrder] = useState("desc");

  // Filters — initialized from URL params if present
  const [searchInput, setSearchInput] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [entityFilter, setEntityFilter] = useState<string | undefined>(initParams?.entity);
  const [accountFilter, setAccountFilter] = useState<string[]>(initParams?.account ? [initParams.account] : []);
  const [ccyFilter, setCcyFilter] = useState<string>();
  const [managementFilter, setManagementFilter] = useState<string | undefined>(initParams?.management);
  const [groupingFilter, setGroupingFilter] = useState<string | undefined>(initParams?.grouping);
  const [classNameFilter, setClassNameFilter] = useState<string | undefined>(initParams?.class_name);
  const [cfLineFilter, setCfLineFilter] = useState<string | undefined>(initParams?.cf_line);
  const [unclassifiedFilter, setUnclassifiedFilter] = useState(initParams?.unclassified || false);
  const [dateRange, setDateRange] = useState<[string, string] | null>(initParams?.dateRange || null);

  // Options
  const [entities, setEntities] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<string[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [managements, setManagements] = useState<string[]>([]);
  const [categoryTree, setCategoryTree] = useState<CategoryNode[]>([]);

  // Editing
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);

  // Bulk edit modal
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkForm] = Form.useForm();

  // Create modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();
  const createEntity = Form.useWatch("entity", createForm);

  const refreshBankAccounts = useCallback(() => {
    listBankAccounts().then((accts) => {
      setBankAccounts(accts);
      setEntities([...new Set(accts.map((a) => a.entity))]);
      setAccounts(accts.map((a) => a.account));
    });
  }, []);

  // Load filter options
  useEffect(() => {
    getCategoryTree().then(setCategoryTree);
    getCategoriesFlat(3).then((nodes) =>
      setManagements(nodes.map((n) => n.name))
    );
    refreshBankAccounts();
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      if (searchTerm) params.search = searchTerm;
      if (entityFilter) params.entity = entityFilter;
      if (accountFilter.length) params.account = accountFilter.join(",");
      if (ccyFilter) params.ccy = ccyFilter;
      if (managementFilter) params.management = managementFilter;
      if (groupingFilter) params.grouping = groupingFilter;
      if (classNameFilter) params.class_name = classNameFilter;
      if (cfLineFilter) params.cf_line = cfLineFilter;
      if (unclassifiedFilter) params.unclassified = true;
      if (dateRange) {
        params.start_date = dateRange[0];
        params.end_date = dateRange[1];
      }

      const res = await listTransactions(params);
      setData(res.items);
      setTotal(res.total);
      setSumCf(res.sum_cf);
      setSumCfInCny(res.sum_cf_in_cny);
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  }, [
    page, pageSize, sortBy, sortOrder, searchTerm,
    entityFilter, accountFilter, ccyFilter,
    managementFilter, groupingFilter, classNameFilter, cfLineFilter,
    unclassifiedFilter, dateRange,
  ]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleManagementCascade = async (mgmt: string, targetForm: ReturnType<typeof Form.useForm>[0]) => {
    if (!mgmt) return;
    try {
      const lookup = await lookupCategory(mgmt);
      targetForm.setFieldsValue({
        grouping: lookup.grouping || "",
        class_name: lookup.class_name || "",
        cf_line: lookup.cf_line || "",
      });
    } catch {
      // lookup failed
    }
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      const payload: Record<string, unknown> = {
        ...values,
        period: values.period.format("YYYY-MM-DD"),
      };
      await createTransaction(payload);
      message.success("新增成功");
      setCreateModalOpen(false);
      createForm.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.response?.status === 409) {
        message.error("重复流水记录");
      } else if (err?.errorFields) {
        // form validation error, ignore
      } else {
        message.error("新增失败");
      }
    }
  };

  const handleSave = async (id: number) => {
    try {
      const values = editForm.getFieldsValue();
      await updateTransaction(id, values);
      message.success("保存成功");
      setEditingId(null);
      fetchData();
    } catch {
      message.error("保存失败");
    }
  };

  const handleBulkUpdate = async () => {
    try {
      const values = bulkForm.getFieldsValue();
      await bulkUpdateTransactions({ ids: selectedRowKeys, ...values });
      message.success(`批量更新 ${selectedRowKeys.length} 条`);
      setBulkModalOpen(false);
      setSelectedRowKeys([]);
      fetchData();
    } catch {
      message.error("批量更新失败");
    }
  };

  const [reclassifying, setReclassifying] = useState(false);
  const [fixingRates, setFixingRates] = useState(false);

  const handleFixRates = async () => {
    setFixingRates(true);
    try {
      const result = await fixExchangeRates(true);
      if (result.fixed === 0) {
        message.info("所有汇率已是最新，无需修正");
      } else {
        message.success(`已修正 ${result.fixed} 条交易的汇率（共 ${result.total} 条非CNY交易）`);
      }
      fetchData();
    } catch {
      message.error("修正汇率失败");
    } finally {
      setFixingRates(false);
    }
  };

  const handleReclassify = async () => {
    setReclassifying(true);
    try {
      const result = await reclassifyTransactions();
      if (result.total_unclassified === 0) {
        message.info("没有未分类的流水");
      } else {
        message.success(
          `更新分类完成: 共 ${result.total_unclassified} 条未分类, 成功分类 ${result.classified} 条, 仍未分类 ${result.still_unclassified} 条`
        );
        fetchData();
      }
    } catch {
      message.error("更新分类失败");
    } finally {
      setReclassifying(false);
    }
  };

  const handleExport = async () => {
    try {
      const params: Record<string, unknown> = {};
      if (entityFilter) params.entity = entityFilter;
      if (accountFilter.length) params.account = accountFilter.join(",");
      if (ccyFilter) params.ccy = ccyFilter;
      if (managementFilter) params.management = managementFilter;
      if (groupingFilter) params.grouping = groupingFilter;
      if (classNameFilter) params.class_name = classNameFilter;
      if (cfLineFilter) params.cf_line = cfLineFilter;
      if (unclassifiedFilter) params.unclassified = true;
      if (searchTerm) params.search = searchTerm;
      if (dateRange) {
        params.start_date = dateRange[0];
        params.end_date = dateRange[1];
      }
      const blob = await exportTransactions(params);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "transactions.xlsx";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error("导出失败");
    }
  };

  const handleBulkDelete = () => {
    // Build description of what will be deleted
    const filters: string[] = [];
    if (selectedRowKeys.length > 0) {
      filters.push(`已选中 ${selectedRowKeys.length} 条`);
    } else {
      if (entityFilter) filters.push(`实体: ${entityFilter}`);
      if (accountFilter.length) filters.push(`账户: ${accountFilter.join(", ")}`);
      if (ccyFilter) filters.push(`币种: ${ccyFilter}`);
      if (managementFilter) filters.push(`科目: ${managementFilter}`);
      if (groupingFilter) filters.push(`类别: ${groupingFilter}`);
      if (classNameFilter) filters.push(`分组: ${classNameFilter}`);
      if (unclassifiedFilter) filters.push("仅未分类");
      if (dateRange) filters.push(`日期: ${dateRange[0]} ~ ${dateRange[1]}`);
      if (searchTerm) filters.push(`搜索: ${searchTerm}`);
    }

    if (filters.length === 0) {
      message.warning("请先设置筛选条件或勾选记录");
      return;
    }

    const desc = selectedRowKeys.length > 0
      ? `确定删除选中的 ${selectedRowKeys.length} 条记录？`
      : `确定删除筛选结果中的 ${total} 条记录？\n条件: ${filters.join(", ")}`;

    Modal.confirm({
      title: "批量删除",
      content: desc,
      okText: "删除",
      okType: "danger",
      onOk: async () => {
        try {
          const params: Record<string, unknown> = {};
          if (selectedRowKeys.length > 0) {
            params.ids = selectedRowKeys.join(",");
          } else {
            if (entityFilter) params.entity = entityFilter;
            if (accountFilter.length) params.account = accountFilter.join(",");
            if (ccyFilter) params.ccy = ccyFilter;
            if (managementFilter) params.management = managementFilter;
            if (groupingFilter) params.grouping = groupingFilter;
            if (classNameFilter) params.class_name = classNameFilter;
            if (unclassifiedFilter) params.unclassified = true;
            if (dateRange) {
              params.start_date = dateRange[0];
              params.end_date = dateRange[1];
            }
            if (searchTerm) params.search = searchTerm;
          }
          const result = await bulkDeleteTransactions(params);
          message.success(`已删除 ${result.deleted} 条记录`);
          setSelectedRowKeys([]);
          setPage(1);
          fetchData();
        } catch {
          message.error("删除失败");
        }
      },
    });
  };

  const [colWidths, setColWidths] = useState<Record<string, number>>({
    period: 100,
    entity: 90,
    account: 120,
    counterpart: 140,
    abstract: 180,
    ccy: 55,
    cf: 110,
    exchange_rate: 70,
    cf_in_cny: 110,
    management: 160,
    grouping: 150,
    classification_method: 70,
    import_batch: 80,
    action: 80,
  });

  const handleResize = (key: string) => (_: any, { size }: { size: { width: number } }) => {
    setColWidths((prev) => ({ ...prev, [key]: size.width }));
  };

  const baseColumns = [
    { key: "period", title: "日期", dataIndex: "period", sorter: true },
    { key: "entity", title: "实体", dataIndex: "entity" },
    { key: "account", title: "账户", dataIndex: "account", ellipsis: true },
    { key: "counterpart", title: "交易对方", dataIndex: "counterpart", ellipsis: true },
    { key: "abstract", title: "摘要", dataIndex: "abstract", ellipsis: true },
    { key: "ccy", title: "币种", dataIndex: "ccy" },
    {
      key: "cf",
      title: "金额",
      dataIndex: "cf",
      sorter: true,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? "#52c41a" : "#f5222d", fontWeight: 500 }}>
          {v?.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      key: "exchange_rate",
      title: "汇率",
      dataIndex: "exchange_rate",
      render: (v: number) => v !== 1 ? v?.toFixed(2) : "-",
    },
    {
      key: "cf_in_cny",
      title: "CNY金额",
      dataIndex: "cf_in_cny",
      sorter: true,
      render: (v: number) => v?.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    },
    {
      key: "management",
      title: "Management",
      dataIndex: "management",
      render: (v: string | null, record: Transaction) => {
        if (editingId === record.id) {
          return (
            <Form.Item name="management" style={{ margin: 0 }}>
              <AutoComplete
                style={{ width: "100%" }}
                options={managements.map((m) => ({ value: m, label: m }))}
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
                onSelect={(val) => handleManagementCascade(val, editForm)}
                placeholder="选择或输入"
              />
            </Form.Item>
          );
        }
        return v ? (
          <Tag color="blue">{v}</Tag>
        ) : (
          <Tag color="orange">未分类</Tag>
        );
      },
    },
    {
      key: "grouping",
      title: "Grouping",
      dataIndex: "grouping",
      ellipsis: true,
    },
    {
      key: "classification_method",
      title: "方法",
      dataIndex: "classification_method",
      render: (v: string | null) => {
        const colors: Record<string, string> = {
          keyword: "green",
          ai: "purple",
          manual: "blue",
          learning: "cyan",
          seed: "default",
        };
        return v ? <Tag color={colors[v] || "default"}>{v}</Tag> : null;
      },
    },
    {
      key: "import_batch",
      title: "来源",
      dataIndex: "import_batch",
      ellipsis: true,
      render: (v: string | null) => {
        if (!v) return null;
        if (v === "seed") return <Tag>种子</Tag>;
        return <Tag color="cyan">{v}</Tag>;
      },
    },
    {
      key: "action",
      title: "操作",
      fixed: "right" as const,
      render: (_: unknown, record: Transaction) => {
        if (editingId === record.id) {
          return (
            <Space>
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleSave(record.id)}
              />
              <Button type="link" size="small" onClick={() => setEditingId(null)}>
                取消
              </Button>
            </Space>
          );
        }
        return (
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingId(record.id);
              editForm.setFieldsValue({
                management: record.management,
                grouping: record.grouping,
                class_name: record.class_name,
                cf_line: record.cf_line,
              });
            }}
          >
            编辑
          </Button>
        );
      },
    },
  ];

  const columns = baseColumns.map((col) => ({
    ...col,
    width: colWidths[col.key],
    onHeaderCell: (column: any) => ({
      width: column.width,
      onResize: handleResize(col.key),
    }),
  }));

  const drilldownTags = [
    classNameFilter && { label: `分组: ${classNameFilter}`, clear: () => { setClassNameFilter(undefined); setPage(1); } },
    groupingFilter && { label: `类别: ${groupingFilter}`, clear: () => { setGroupingFilter(undefined); setPage(1); } },
    managementFilter && { label: `科目: ${managementFilter}`, clear: () => { setManagementFilter(undefined); setPage(1); } },
    cfLineFilter && { label: `现金流: ${cfLineFilter}`, clear: () => { setCfLineFilter(undefined); setPage(1); } },
  ].filter(Boolean) as { label: string; clear: () => void }[];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        {drilldownTags.length > 0 && (
          <Row style={{ marginBottom: 12 }}>
            <Space wrap>
              <span style={{ fontSize: 12, color: "#888" }}>报表筛选:</span>
              {drilldownTags.map((t) => (
                <Tag
                  key={t.label}
                  closable
                  color="blue"
                  onClose={t.clear}
                >
                  {t.label}
                </Tag>
              ))}
              <Button
                type="link"
                size="small"
                onClick={() => {
                  setManagementFilter(undefined);
                  setGroupingFilter(undefined);
                  setClassNameFilter(undefined);
                  setCfLineFilter(undefined);
                  setPage(1);
                }}
              >
                清除报表筛选
              </Button>
            </Space>
          </Row>
        )}
        <Row gutter={[12, 12]}>
          <Col span={6}>
            <Input
              placeholder="搜索摘要/交易对方/金额"
              prefix={<SearchOutlined />}
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                if (!e.target.value) { setSearchTerm(""); setPage(1); }
              }}
              onPressEnter={() => { setSearchTerm(searchInput); setPage(1); }}
              allowClear
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="实体"
              allowClear
              style={{ width: "100%" }}
              value={entityFilter}
              onChange={(v) => { setEntityFilter(v); setAccountFilter([]); setPage(1); }}
              options={entities.map((e) => ({ value: e, label: e }))}
            />
          </Col>
          <Col span={4}>
            <Select
              mode="multiple"
              placeholder="账户"
              allowClear
              maxTagCount="responsive"
              style={{ width: "100%" }}
              value={accountFilter}
              onChange={(v) => { setAccountFilter(v); setPage(1); }}
              options={[
                { value: "未知账户", label: "未知账户" },
                ...(entityFilter
                  ? bankAccounts.filter((a) => a.entity === entityFilter)
                  : bankAccounts
                ).map((a) => ({ value: a.account, label: a.account })),
              ]}
            />
          </Col>
          <Col span={3}>
            <Select
              placeholder="币种"
              allowClear
              style={{ width: "100%" }}
              value={ccyFilter}
              onChange={(v) => { setCcyFilter(v); setPage(1); }}
              options={["CNY", "USD", "SGD", "HKD"].map((c) => ({ value: c, label: c }))}
            />
          </Col>
          <Col span={7}>
            <RangePicker
              style={{ width: "100%" }}
              value={dateRange ? [dayjs(dateRange[0]), dayjs(dateRange[1])] : null}
              onChange={(_, ds) => {
                setDateRange(ds[0] && ds[1] ? [ds[0], ds[1]] : null);
                setPage(1);
              }}
            />
          </Col>
        </Row>
        <Row style={{ marginTop: 12 }} justify="end">
          <Space wrap>
            <Button
              type={unclassifiedFilter ? "primary" : "default"}
              onClick={() => { setUnclassifiedFilter(!unclassifiedFilter); setPage(1); }}
            >
              仅未分类
            </Button>
            <Button
              icon={<ThunderboltOutlined />}
              loading={reclassifying}
              onClick={handleReclassify}
            >
              更新分类
            </Button>
            <Button
              icon={<DollarOutlined />}
              loading={fixingRates}
              onClick={handleFixRates}
            >
              修正汇率
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleBulkDelete}
            >
              批量删除{selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length})` : ""}
            </Button>
            {selectedRowKeys.length > 0 && (
              <Button type="primary" onClick={() => { bulkForm.resetFields(); refreshBankAccounts(); setBulkModalOpen(true); }}>
                批量编辑 ({selectedRowKeys.length})
              </Button>
            )}
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => { createForm.resetFields(); refreshBankAccounts(); setCreateModalOpen(true); }}
            >
              新增流水
            </Button>
          </Space>
        </Row>
      </Card>

      {selectedRowKeys.length > 0 && (() => {
        const sel = data.filter((t) => selectedRowKeys.includes(t.id));
        const selCf = sel.reduce((s, t) => s + (t.cf || 0), 0);
        const selCny = sel.reduce((s, t) => s + (t.cf_in_cny || 0), 0);
        const fmt = (v: number) => v.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return (
          <div
            style={{
              display: "flex",
              gap: 24,
              padding: "8px 16px",
              marginBottom: 8,
              background: "#e6f4ff",
              borderRadius: 6,
              fontSize: 13,
              alignItems: "center",
              border: "1px solid #91caff",
            }}
          >
            <span style={{ color: "#1677ff", fontWeight: 500 }}>已选 {selectedRowKeys.length} 条</span>
            <span>
              原币合计{" "}
              <span style={{ fontWeight: 600, color: selCf >= 0 ? "#389e0d" : "#cf1322", fontVariantNumeric: "tabular-nums" }}>
                {fmt(selCf)}
              </span>
            </span>
            <span>
              CNY 合计{" "}
              <span style={{ fontWeight: 600, color: selCny >= 0 ? "#389e0d" : "#cf1322", fontVariantNumeric: "tabular-nums" }}>
                {fmt(selCny)}
              </span>
            </span>
          </div>
        );
      })()}

      <Form form={editForm} component={false}>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={data}
          columns={columns}
          components={{ header: { cell: ResizableTitle } }}
          size="small"
          scroll={{ x: Object.values(colWidths).reduce((a, b) => a + b, 0) }}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as number[]),
          }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ["20", "50", "100", "200"],
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
          onChange={(_pagination, _filters, sorter: any) => {
            if (sorter.field) {
              setSortBy(sorter.field);
              setSortOrder(sorter.order === "ascend" ? "asc" : "desc");
            }
          }}
        />
      </Form>

      <Modal
        title={`批量编辑 ${selectedRowKeys.length} 条记录`}
        open={bulkModalOpen}
        onOk={handleBulkUpdate}
        onCancel={() => setBulkModalOpen(false)}
      >
        <Form form={bulkForm} layout="vertical">
          <Form.Item name="entity" label="实体" extra="留空则不改；用于修正「未知账户」等">
            <Select
              allowClear
              showSearch
              placeholder="不改则留空"
              options={entities.map((e) => ({ value: e, label: e }))}
            />
          </Form.Item>
          <Form.Item name="account" label="账户">
            <Select
              allowClear
              showSearch
              placeholder="不改则留空"
              options={[...new Set(bankAccounts.map((a) => a.account))].map((a) => ({ value: a, label: a }))}
            />
          </Form.Item>
          <Form.Item name="management" label="Management">
            <AutoComplete
              options={managements.map((m) => ({ value: m, label: m }))}
              filterOption={(input, option) =>
                (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
              }
              onSelect={(val) => handleManagementCascade(val, bulkForm)}
              placeholder="选择或输入自定义分类"
            />
          </Form.Item>
          <Form.Item name="grouping" label="Grouping">
            <Input placeholder="选择 Management 后自动填充，或手动输入" />
          </Form.Item>
          <Form.Item name="class_name" label="Class">
            <Input placeholder="选择 Management 后自动填充，或手动输入" />
          </Form.Item>
          <Form.Item name="cf_line" label="CF Line">
            <Input placeholder="选择 Management 后自动填充，或手动输入" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="新增流水"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => setCreateModalOpen(false)}
        width={640}
      >
        <Form form={createForm} layout="vertical" initialValues={{ ccy: "CNY", cf: 0 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="entity" label="实体" rules={[{ required: true }]}>
                <Select
                  showSearch
                  options={entities.map((e) => ({ value: e, label: e }))}
                  onChange={(v) => {
                    // Auto-set account options based on entity
                    const matched = bankAccounts.filter((a) => a.entity === v);
                    if (matched.length === 1) {
                      createForm.setFieldsValue({ account: matched[0].account, ccy: matched[0].ccy });
                    } else {
                      createForm.setFieldsValue({ account: undefined });
                    }
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="account" label="账户" rules={[{ required: true }]}>
                <Select
                  showSearch
                  options={(createEntity
                    ? bankAccounts.filter((a) => a.entity === createEntity)
                    : bankAccounts
                  ).map((a) => ({ value: a.account, label: a.account }))}
                  onChange={(v) => {
                    const acct = bankAccounts.find((a) => a.account === v);
                    if (acct) createForm.setFieldsValue({ ccy: acct.ccy });
                  }}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="period" label="日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="cf" label="金额" rules={[{ required: true }]}>
                <InputNumber style={{ width: "100%" }} step={0.01} placeholder="收入为正, 支出为负" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="ccy" label="币种">
                <Select options={["CNY", "USD", "SGD", "HKD"].map((c) => ({ value: c, label: c }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="counterpart" label="交易对方">
            <Input />
          </Form.Item>
          <Form.Item name="abstract" label="摘要">
            <Input />
          </Form.Item>
          <Form.Item name="note" label="备注">
            <Input />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="management" label="Management">
                <AutoComplete
                  options={managements.map((m) => ({ value: m, label: m }))}
                  filterOption={(input, option) =>
                    (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                  onSelect={(val) => handleManagementCascade(val, createForm)}
                  placeholder="选择或输入"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="grouping" label="Grouping">
                <Input placeholder="选择 Management 后自动填充" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}
