import { useState, useEffect } from "react";
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Tag,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ImportTemplate } from "../../types";
import { listTemplates, createTemplate, updateTemplate, deleteTemplate } from "../../api/client";

const { TextArea } = Input;

export default function ImportTemplatesPage() {
  const [data, setData] = useState<ImportTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      setData(await listTemplates());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    // Parse config JSON
    try {
      values.config = JSON.parse(values.config);
    } catch {
      message.error("配置JSON格式错误");
      return;
    }

    try {
      if (editingId) {
        await updateTemplate(editingId, values);
        message.success("更新成功");
      } else {
        await createTemplate(values);
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
    await deleteTemplate(id);
    message.success("已删除");
    fetchData();
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "模板名称", dataIndex: "name", width: 140 },
    {
      title: "银行类型",
      dataIndex: "bank_type",
      width: 100,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    { title: "描述", dataIndex: "description", width: 250, ellipsis: true },
    {
      title: "配置",
      dataIndex: "config",
      width: 300,
      ellipsis: true,
      render: (v: Record<string, unknown>) => (
        <code style={{ fontSize: 12 }}>{JSON.stringify(v)}</code>
      ),
    },
    {
      title: "操作",
      width: 120,
      render: (_: unknown, record: ImportTemplate) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingId(record.id);
              form.setFieldsValue({
                ...record,
                config: JSON.stringify(record.config, null, 2),
              });
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
      title="导入模板配置"
      extra={
        <Space>
          <Button onClick={fetchData}>刷新</Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingId(null);
              form.resetFields();
              form.setFieldsValue({ config: "{}" });
              setModalOpen(true);
            }}
          >
            新增模板
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
      />

      <Modal
        title={editingId ? "编辑模板" : "新增模板"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingId(null); }}
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="bank_type" label="银行类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "cmb", label: "招商银行" },
                { value: "citic", label: "中信银行" },
                { value: "airwallex", label: "Airwallex" },
                { value: "dbs", label: "DBS" },
              ]}
            />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input />
          </Form.Item>
          <Form.Item name="config" label="配置 (JSON)" rules={[{ required: true }]}>
            <TextArea rows={12} style={{ fontFamily: "monospace" }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
