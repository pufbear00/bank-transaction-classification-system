import { useState, useEffect } from "react";
import {
  Card,
  Tree,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Popconfirm,
  Tag,
  Empty,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { CategoryNode } from "../../types";
import { getCategoryTree, createCategory, updateCategory, deleteCategory } from "../../api/client";

function toTreeData(nodes: CategoryNode[]): any[] {
  return nodes.map((n) => ({
    key: n.id,
    title: (
      <span>
        {n.name}
        {n.level === 1 && <Tag color="blue" style={{ marginLeft: 8 }}>L1 Grouping</Tag>}
        {n.level === 2 && <Tag color="green" style={{ marginLeft: 8 }}>L2 Class</Tag>}
        {n.level === 3 && (
          <>
            <Tag color="orange" style={{ marginLeft: 8 }}>L3 Management</Tag>
            {n.cf_line && <Tag style={{ marginLeft: 4 }}>{n.cf_line}</Tag>}
          </>
        )}
      </span>
    ),
    node: n,
    children: n.children?.length ? toTreeData(n.children) : undefined,
  }));
}

export default function CategoryTreePage() {
  const [tree, setTree] = useState<CategoryNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<CategoryNode | null>(null);
  const [parentId, setParentId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const fetchTree = async () => {
    setLoading(true);
    try {
      const data = await getCategoryTree();
      setTree(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTree(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    try {
      if (editingNode) {
        await updateCategory(editingNode.id, values);
        message.success("更新成功");
      } else {
        await createCategory({ ...values, parent_id: parentId });
        message.success("创建成功");
      }
      setModalOpen(false);
      form.resetFields();
      setEditingNode(null);
      fetchTree();
    } catch {
      message.error("操作失败");
    }
  };

  const handleDelete = async (id: number) => {
    await deleteCategory(id);
    message.success("已删除");
    fetchTree();
  };

  const treeData = toTreeData(tree);

  return (
    <Card
      title="分类体系管理"
      extra={
        <Space>
          <Button onClick={fetchTree}>刷新</Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingNode(null);
              setParentId(null);
              form.resetFields();
              form.setFieldsValue({ level: 1 });
              setModalOpen(true);
            }}
          >
            新增根节点
          </Button>
        </Space>
      }
    >
      {treeData.length === 0 ? (
        <Empty description="暂无分类数据" />
      ) : (
        <Tree
          treeData={treeData}
          defaultExpandAll
          blockNode
          titleRender={(nodeData: any) => (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{nodeData.title}</span>
              <Space size={0}>
                {nodeData.node.level < 3 && (
                  <Button
                    type="link"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingNode(null);
                      setParentId(nodeData.node.id);
                      form.resetFields();
                      form.setFieldsValue({ level: nodeData.node.level + 1 });
                      setModalOpen(true);
                    }}
                  />
                )}
                <Button
                  type="link"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingNode(nodeData.node);
                    form.setFieldsValue(nodeData.node);
                    setModalOpen(true);
                  }}
                />
                <Popconfirm
                  title="确定删除? 子节点也会被删除"
                  onConfirm={(e) => {
                    e?.stopPropagation();
                    handleDelete(nodeData.node.id);
                  }}
                >
                  <Button
                    type="link"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>
              </Space>
            </div>
          )}
        />
      )}

      <Modal
        title={editingNode ? "编辑节点" : "新增节点"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingNode(null); }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="level" label="层级">
            <Select
              disabled
              options={[
                { value: 1, label: "L1 - Grouping" },
                { value: 2, label: "L2 - Class" },
                { value: 3, label: "L3 - Management" },
              ]}
            />
          </Form.Item>
          <Form.Item name="cf_line" label="CF Line (仅L3)">
            <Input />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
