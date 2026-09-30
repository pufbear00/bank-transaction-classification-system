import { Layout, Menu } from "antd";
import {
  UploadOutlined,
  TableOutlined,
  BarChartOutlined,
  DollarOutlined,
  ScheduleOutlined,
  TagsOutlined,
  ApartmentOutlined,
  BankOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { Outlet, useNavigate, useLocation } from "react-router-dom";

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: "/import", icon: <UploadOutlined />, label: "流水导入" },
  { key: "/transactions", icon: <TableOutlined />, label: "统一流水表" },
  { key: "/report", icon: <BarChartOutlined />, label: "月度汇总报表" },
  { key: "/cash-balance", icon: <DollarOutlined />, label: "现金余额" },
  { key: "/amortization", icon: <ScheduleOutlined />, label: "摊销管理" },
  { key: "/rules", icon: <TagsOutlined />, label: "分类映射管理" },
  { key: "/categories", icon: <ApartmentOutlined />, label: "分类体系管理" },
  { key: "/accounts", icon: <BankOutlined />, label: "银行账户管理" },
  { key: "/templates", icon: <SettingOutlined />, label: "导入模板配置" },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={200} theme="dark">
        <div
          style={{
            height: 48,
            margin: 16,
            color: "#fff",
            fontSize: 16,
            fontWeight: 600,
            textAlign: "center",
            lineHeight: "48px",
          }}
        >
          银行流水管理
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            fontSize: 18,
            fontWeight: 500,
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          银行流水 · 本地空数据版（无外部同步，仅使用虚构资料）
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
