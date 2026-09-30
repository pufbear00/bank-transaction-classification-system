import { useState, useEffect, useMemo } from "react";
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  DatePicker,
  Steps,
  message,
  Popconfirm,
  Tag,
  Progress,
} from "antd";
import { PlusOutlined, DeleteOutlined, SearchOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import type { Amortization, AmortizationEntry, CategoryNode, Transaction } from "../../types";
import {
  listAmortizations,
  createAmortization,
  getAmortizationDetail,
  deleteAmortization,
  getCategoriesFlat,
  lookupCategory,
  listBankAccounts,
  listTransactions,
} from "../../api/client";

const { RangePicker } = DatePicker;

export default function AmortizationPage() {
  const [data, setData] = useState<Amortization[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const [mgmtOptions, setMgmtOptions] = useState<CategoryNode[]>([]);
  const [entities, setEntities] = useState<string[]>([]);
  const [expandedEntries, setExpandedEntries] = useState<Record<number, AmortizationEntry[]>>({});

  // wizard state
  const [step, setStep] = useState(0);
  const [txnList, setTxnList] = useState<Transaction[]>([]);
  const [txnLoading, setTxnLoading] = useState(false);
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [searchEntity, setSearchEntity] = useState<string | undefined>();
  const [searchDateRange, setSearchDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      setData(await listAmortizations());
    } finally {
      setLoading(false);
    }
  };

  const fetchMeta = async () => {
    try {
      const [cats, accounts] = await Promise.all([
        getCategoriesFlat(3),
        listBankAccounts(),
      ]);
      setMgmtOptions(cats);
      const uniqueEntities = [...new Set(accounts.map((a) => a.entity))];
      setEntities(uniqueEntities);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchData();
    fetchMeta();
  }, []);

  const totalAmount = Form.useWatch("total_amount", form);
  const months = Form.useWatch("months", form);
  const monthlyAmount = useMemo(() => {
    if (totalAmount && months && months > 0) {
      return Math.round((totalAmount / months) * 100) / 100;
    }
    return 0;
  }, [totalAmount, months]);

  const handleExpenseChange = async (value: string) => {
    try {
      const lookup = await lookupCategory(value);
      if (lookup) {
        form.setFieldsValue({
          grouping: lookup.grouping,
          class_name: lookup.class_name,
        });
      }
    } catch {
      // ignore
    }
  };

  // Step 1: search transactions
  const handleSearchTxn = async () => {
    setTxnLoading(true);
    try {
      const params: Record<string, unknown> = { page_size: 50 };
      if (searchKeyword.trim()) params.search = searchKeyword.trim();
      if (searchEntity) params.entity = searchEntity;
      if (searchDateRange) {
        params.start_date = searchDateRange[0].format("YYYY-MM-DD");
        params.end_date = searchDateRange[1].format("YYYY-MM-DD");
      }
      const res = await listTransactions(params);
      setTxnList(res.items);
    } catch {
      message.error("搜索失败");
    } finally {
      setTxnLoading(false);
    }
  };

  // Step 1 → Step 2: select a transaction and prefill form
  const handleSelectTxn = (txn: Transaction) => {
    setSelectedTxn(txn);
    form.setFieldsValue({
      entity: txn.entity,
      total_amount: Math.abs(txn.cf),
      start_date: dayjs(txn.period),
      source_transaction_id: txn.id,
    });
    setStep(1);
  };

  // Step 2: submit
  const handleCreate = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      const startDate = values.start_date.format("YYYY-MM-DD");
      await createAmortization({
        entity: values.entity,
        total_amount: values.total_amount,
        start_date: startDate,
        months: values.months,
        prepaid_account: values.prepaid_account,
        expense_account: values.expense_account,
        grouping: values.grouping,
        class_name: values.class_name,
        source_transaction_id: values.source_transaction_id,
      });
      message.success("摊销计划创建成功");
      handleCloseModal();
      fetchData();
    } catch {
      message.error("创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenModal = () => {
    form.resetFields();
    setStep(0);
    setTxnList([]);
    setSelectedTxn(null);
    setSearchKeyword("");
    setSearchEntity(undefined);
    setSearchDateRange(null);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    form.resetFields();
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteAmortization(id);
      message.success("已删除摊销及关联分录");
      fetchData();
    } catch {
      message.error("删除失败");
    }
  };

  const handleExpand = async (expanded: boolean, record: Amortization) => {
    if (expanded && !expandedEntries[record.id]) {
      try {
        const detail = await getAmortizationDetail(record.id);
        setExpandedEntries((prev) => ({ ...prev, [record.id]: detail.entries }));
      } catch {
        message.error("加载明细失败");
      }
    }
  };

  const mgmtSelectOptions = mgmtOptions.map((c) => ({
    value: c.name,
    label: c.name,
  }));

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "实体", dataIndex: "entity", width: 100 },
    { title: "费用科目", dataIndex: "expense_account", width: 180 },
    { title: "预付科目", dataIndex: "prepaid_account", width: 180 },
    {
      title: "总额",
      dataIndex: "total_amount",
      width: 120,
      render: (v: number) => v?.toLocaleString("zh-CN", { minimumFractionDigits: 2 }),
    },
    {
      title: "月额",
      dataIndex: "monthly_amount",
      width: 110,
      render: (v: number) => v?.toLocaleString("zh-CN", { minimumFractionDigits: 2 }),
    },
    { title: "月数", dataIndex: "months", width: 60 },
    {
      title: "开始日期",
      dataIndex: "start_date",
      width: 110,
      render: (v: string) => v?.slice(0, 7),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (v: string) => (
        <Tag color={v === "completed" ? "green" : "blue"}>
          {v === "completed" ? "已完成" : "进行中"}
        </Tag>
      ),
    },
    {
      title: "进度",
      width: 140,
      render: (_: unknown, record: Amortization) => {
        const pct = record.total_entries > 0
          ? Math.round((record.posted_count / record.total_entries) * 100)
          : 0;
        return (
          <Progress
            percent={pct}
            size="small"
            format={() => `${record.posted_count}/${record.total_entries}`}
          />
        );
      },
    },
    {
      title: "操作",
      width: 80,
      render: (_: unknown, record: Amortization) => (
        <Popconfirm
          title="确定删除此摊销计划及所有关联ADJ分录?"
          onConfirm={() => handleDelete(record.id)}
        >
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const entryColumns = [
    {
      title: "月份",
      dataIndex: "period",
      width: 100,
      render: (v: string) => v?.slice(0, 7),
    },
    {
      title: "金额",
      dataIndex: "amount",
      width: 120,
      render: (v: number) => v?.toLocaleString("zh-CN", { minimumFractionDigits: 2 }),
    },
    {
      title: "已过账",
      dataIndex: "is_posted",
      width: 80,
      render: (v: boolean) => (
        <Tag color={v ? "green" : "default"}>{v ? "是" : "否"}</Tag>
      ),
    },
    {
      title: "借方交易ID",
      dataIndex: "debit_transaction_id",
      width: 110,
      render: (v: number | null) => v ?? "-",
    },
    {
      title: "贷方交易ID",
      dataIndex: "credit_transaction_id",
      width: 110,
      render: (v: number | null) => v ?? "-",
    },
  ];

  // Step 1 transaction search result columns
  const txnColumns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "实体", dataIndex: "entity", width: 100 },
    { title: "账户", dataIndex: "account", width: 120 },
    {
      title: "日期",
      dataIndex: "period",
      width: 100,
      render: (v: string) => v?.slice(0, 10),
    },
    {
      title: "摘要",
      dataIndex: "abstract",
      ellipsis: true,
      render: (v: string | null) => v || "-",
    },
    {
      title: "对方",
      dataIndex: "counterpart",
      width: 120,
      ellipsis: true,
      render: (v: string | null) => v || "-",
    },
    {
      title: "金额",
      dataIndex: "cf",
      width: 120,
      render: (v: number, r: Transaction) =>
        `${v?.toLocaleString("zh-CN", { minimumFractionDigits: 2 })} ${r.ccy}`,
    },
  ];

  return (
    <Card
      title="摊销管理"
      extra={
        <Space>
          <Button onClick={fetchData}>刷新</Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleOpenModal}
          >
            新建摊销
          </Button>
        </Space>
      }
    >
      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        columns={columns}
        size="small"
        pagination={false}
        expandable={{
          onExpand: handleExpand,
          expandedRowRender: (record: Amortization) => (
            <Table
              rowKey="id"
              dataSource={expandedEntries[record.id] || []}
              columns={entryColumns}
              size="small"
              pagination={false}
            />
          ),
        }}
      />

      <Modal
        title="新建摊销计划"
        open={modalOpen}
        onCancel={handleCloseModal}
        width={800}
        footer={
          step === 0
            ? [
                <Button key="cancel" onClick={handleCloseModal}>
                  取消
                </Button>,
              ]
            : [
                <Button key="back" onClick={() => setStep(0)}>
                  上一步
                </Button>,
                <Button
                  key="submit"
                  type="primary"
                  loading={submitting}
                  onClick={handleCreate}
                >
                  创建
                </Button>,
              ]
        }
      >
        <Steps
          current={step}
          size="small"
          style={{ marginBottom: 24 }}
          items={[
            { title: "选择流水" },
            { title: "确认摊销参数" },
          ]}
        />

        {step === 0 && (
          <>
            <Space wrap style={{ marginBottom: 16 }}>
              <Input
                placeholder="关键词搜索"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onPressEnter={handleSearchTxn}
                style={{ width: 160 }}
              />
              <Select
                placeholder="选择实体"
                allowClear
                value={searchEntity}
                onChange={setSearchEntity}
                options={entities.map((e) => ({ value: e, label: e }))}
                style={{ width: 160 }}
              />
              <RangePicker
                value={searchDateRange}
                onChange={(dates) =>
                  setSearchDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)
                }
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleSearchTxn}
              >
                搜索
              </Button>
            </Space>
            <Table
              rowKey="id"
              loading={txnLoading}
              dataSource={txnList}
              columns={txnColumns}
              size="small"
              pagination={false}
              scroll={{ y: 300 }}
              onRow={(record) => ({
                onClick: () => handleSelectTxn(record),
                style: { cursor: "pointer" },
              })}
            />
          </>
        )}

        {step === 1 && (
          <>
            {selectedTxn && (
              <Card size="small" style={{ marginBottom: 16, background: "#f6f8fa" }}>
                已选流水：
                <strong>
                  {selectedTxn.period.slice(0, 10)} | {selectedTxn.entity} |{" "}
                  {selectedTxn.abstract || "-"} |{" "}
                  {selectedTxn.cf.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}{" "}
                  {selectedTxn.ccy}
                </strong>
              </Card>
            )}
            <Form form={form} layout="vertical">
              <Form.Item name="source_transaction_id" hidden>
                <InputNumber />
              </Form.Item>
              <Form.Item name="entity" label="公司实体" rules={[{ required: true }]}>
                <Select
                  showSearch
                  options={entities.map((e) => ({ value: e, label: e }))}
                />
              </Form.Item>
              <Form.Item
                name="total_amount"
                label="总金额"
                rules={[{ required: true }]}
              >
                <InputNumber style={{ width: "100%" }} min={0.01} precision={2} />
              </Form.Item>
              <Form.Item
                name="start_date"
                label="起始月份"
                rules={[{ required: true }]}
              >
                <DatePicker picker="month" style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item
                name="months"
                label="摊销月数"
                rules={[{ required: true }]}
              >
                <InputNumber style={{ width: "100%" }} min={1} max={120} precision={0} />
              </Form.Item>
              <Form.Item label="每月金额">
                <InputNumber
                  style={{ width: "100%" }}
                  value={monthlyAmount}
                  disabled
                  precision={2}
                />
              </Form.Item>
              <Form.Item
                name="expense_account"
                label="费用科目 (Management)"
                rules={[{ required: true }]}
              >
                <Select
                  showSearch
                  options={mgmtSelectOptions}
                  onChange={handleExpenseChange}
                />
              </Form.Item>
              <Form.Item
                name="prepaid_account"
                label="预付科目 (Management)"
                rules={[{ required: true }]}
              >
                <Select showSearch options={mgmtSelectOptions} />
              </Form.Item>
              <Form.Item name="grouping" label="Grouping">
                <Select showSearch allowClear options={mgmtSelectOptions} />
              </Form.Item>
              <Form.Item name="class_name" label="Class">
                <Select showSearch allowClear options={mgmtSelectOptions} />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </Card>
  );
}
