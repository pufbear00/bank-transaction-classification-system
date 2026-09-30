import { useState, useEffect } from "react";
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Modal,
  Form,
  Select,
  AutoComplete,
  Tag,
  Upload,
  message,
  Popconfirm,
} from "antd";
import { PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined, DownloadOutlined, UploadOutlined } from "@ant-design/icons";
import type { ClassificationRule } from "../../types";
import { listRules, createRule, updateRule, deleteRule, getCategoriesFlat, lookupCategory, exportRules, importRules } from "../../api/client";

export default function ClassificationRulesPage() {
  const [data, setData] = useState<ClassificationRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState<string>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [managements, setManagements] = useState<string[]>([]);
  const [cascadeLoading, setCascadeLoading] = useState(false);

  const handleManagementChange = async (mgmt: string) => {
    if (!mgmt) return;
    setCascadeLoading(true);
    try {
      const lookup = await lookupCategory(mgmt);
      form.setFieldsValue({
        grouping: lookup.grouping || "",
        class_name: lookup.class_name || "",
        cf_line: lookup.cf_line || "",
      });
    } catch {
      // lookup failed, leave fields for manual input
    } finally {
      setCascadeLoading(false);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (search) params.search = search;
      if (sourceFilter) params.source = sourceFilter;
      const res = await listRules(params);
      setData(res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    getCategoriesFlat(3).then((nodes) => setManagements(nodes.map((n) => n.name)));
  }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editingId) {
        await updateRule(editingId, values);
        message.success("更新成功");
      } else {
        await createRule(values);
        message.success("创建成功");
      }
      setModalOpen(false);
      setEditingId(null);
      form.resetFields();
      fetchData();
    } catch {
      message.error("操作失败");
    }
  };

  const handleDelete = async (id: number) => {
    await deleteRule(id);
    message.success("已删除");
    fetchData();
  };

  const handleExport = async () => {
    try {
      const blob = await exportRules();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "classification_rules.xlsx";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error("导出失败");
    }
  };

  const handleImport = async (file: File) => {
    try {
      const result = await importRules(file);
      message.success(`导入完成: 新增 ${result.added} 条, 跳过重复 ${result.skipped} 条`);
      fetchData();
    } catch {
      message.error("导入失败");
    }
  };

  const columns = [
    { title: "关键词", dataIndex: "keyword", width: 160 },
    {
      title: "Management",
      dataIndex: "management",
      width: 180,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    { title: "Grouping", dataIndex: "grouping", width: 180, ellipsis: true },
    { title: "Class", dataIndex: "class_name", width: 120 },
    { title: "CF Line", dataIndex: "cf_line", width: 120 },
    {
      title: "来源",
      dataIndex: "source",
      width: 80,
      render: (v: string) => {
        const colors: Record<string, string> = { seed: "default", manual: "blue", learned: "cyan" };
        return <Tag color={colors[v] || "default"}>{v}</Tag>;
      },
    },
    { title: "命中次数", dataIndex: "match_count", width: 90, sorter: (a: ClassificationRule, b: ClassificationRule) => a.match_count - b.match_count },
    {
      title: "操作",
      width: 120,
      render: (_: unknown, record: ClassificationRule) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingId(record.id);
              form.setFieldsValue(record);
              setModalOpen(true);
            }}
          />
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="分类映射管理"
      extra={
        <Space>
          <Input
            placeholder="搜索关键词/分类"
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onPressEnter={fetchData}
            allowClear
            style={{ width: 200 }}
          />
          <Select
            placeholder="来源"
            allowClear
            style={{ width: 100 }}
            value={sourceFilter}
            onChange={(v) => { setSourceFilter(v); }}
            options={[
              { value: "seed", label: "种子" },
              { value: "manual", label: "手动" },
              { value: "learned", label: "学习" },
            ]}
          />
          <Button onClick={fetchData}>刷新</Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出
          </Button>
          <Upload
            accept=".xlsx,.xls"
            showUploadList={false}
            beforeUpload={(file) => { handleImport(file); return false; }}
          >
            <Button icon={<UploadOutlined />}>导入</Button>
          </Upload>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => { setEditingId(null); form.resetFields(); setModalOpen(true); }}
          >
            新增规则
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
        pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 条` }}
      />

      <Modal
        title={editingId ? "编辑规则" : "新增规则"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingId(null); }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="keyword" label="关键词" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="management" label="Management" rules={[{ required: true }]}>
            <AutoComplete
              options={managements.map((m) => ({ value: m, label: m }))}
              filterOption={(input, opt) => (opt?.label as string)?.toLowerCase().includes(input.toLowerCase())}
              onSelect={handleManagementChange}
              placeholder="选择或输入自定义分类"
            />
          </Form.Item>
          <Form.Item name="grouping" label="Grouping" rules={[{ required: true }]}>
            <Input disabled={cascadeLoading} placeholder="选择 Management 后自动填充，或手动输入" />
          </Form.Item>
          <Form.Item name="class_name" label="Class" rules={[{ required: true }]}>
            <Input disabled={cascadeLoading} placeholder="选择 Management 后自动填充，或手动输入" />
          </Form.Item>
          <Form.Item name="cf_line" label="CF Line">
            <Input disabled={cascadeLoading} placeholder="选择 Management 后自动填充，或手动输入" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
