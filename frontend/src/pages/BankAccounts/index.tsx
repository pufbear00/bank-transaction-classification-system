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
import type { BankAccount } from "../../types";
import { listBankAccounts, createBankAccount, updateBankAccount, deleteBankAccount } from "../../api/client";

export default function BankAccountsPage() {
  const [data, setData] = useState<BankAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      setData(await listBankAccounts());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editingId) {
        await updateBankAccount(editingId, values);
        message.success("更新成功");
      } else {
        await createBankAccount(values);
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
    await deleteBankAccount(id);
    message.success("已删除");
    fetchData();
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "公司实体", dataIndex: "entity", width: 120 },
    { title: "账户名称", dataIndex: "account", width: 180 },
    { title: "账号", dataIndex: "account_number", width: 200 },
    {
      title: "币种",
      dataIndex: "ccy",
      width: 80,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: "银行类型",
      dataIndex: "bank_type",
      width: 100,
      render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : "-",
    },
    {
      title: "操作",
      width: 120,
      render: (_: unknown, record: BankAccount) => (
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
      title="银行账户管理"
      extra={
        <Space>
          <Button onClick={fetchData}>刷新</Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => { setEditingId(null); form.resetFields(); setModalOpen(true); }}
          >
            新增账户
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
        title={editingId ? "编辑账户" : "新增账户"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingId(null); }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="entity" label="公司实体" rules={[{ required: true }]}>
            <Input placeholder="请填写自定义演示主体，不要输入真实业务资料" />
          </Form.Item>
          <Form.Item name="account" label="账户名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="account_number" label="银行账号">
            <Input />
          </Form.Item>
          <Form.Item name="ccy" label="币种" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "CNY", label: "CNY" },
                { value: "USD", label: "USD" },
                { value: "SGD", label: "SGD" },
                { value: "HKD", label: "HKD" },
              ]}
            />
          </Form.Item>
          <Form.Item name="bank_type" label="银行类型">
            <Select
              allowClear
              options={[
                { value: "cmb", label: "招商银行" },
                { value: "citic", label: "中信银行" },
                { value: "airwallex", label: "Airwallex" },
                { value: "dbs", label: "DBS" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
