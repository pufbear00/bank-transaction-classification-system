import { useEffect, useState } from "react";
import {
  Card,
  Upload,
  Button,
  Steps,
  Table,
  Tag,
  message,
  Space,
  Alert,
  Statistic,
  Row,
  Col,
  Result,
  Spin,
  Select,
} from "antd";
import { InboxOutlined } from "@ant-design/icons";
import type { ConfirmImportResponse, BankAccount } from "../../types";
import {
  batchUploadAndParse,
  confirmImport,
  listBankAccounts,
  type BatchParseResponse,
} from "../../api/client";

const { Dragger } = Upload;

const BANK_COLORS: Record<string, string> = {
  cmb: "blue",
  citic: "orange",
  airwallex: "purple",
  dbs: "green",
};

export default function ImportPage() {
  const [step, setStep] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [batchResult, setBatchResult] = useState<BatchParseResponse | null>(null);
  const [importResult, setImportResult] = useState<ConfirmImportResponse | null>(null);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  // 覆盖实体/账户：留空则用各文件自动识别的结果
  const [overrideEntity, setOverrideEntity] = useState<string | undefined>();
  const [overrideAccount, setOverrideAccount] = useState<string | undefined>();

  useEffect(() => {
    listBankAccounts().then(setBankAccounts).catch(() => {});
  }, []);

  const entityOptions = [...new Set(bankAccounts.map((a) => a.entity))];
  const accountOptions = [...new Set(bankAccounts.map((a) => a.account))];
  const needsAccountOverride = Boolean(
    batchResult?.files.some((f) => f.account === "未知账户") && !overrideAccount
  );

  const handleFiles = async (fileList: File[]) => {
    if (fileList.length === 0) return;
    setProcessing(true);
    try {
      const res = await batchUploadAndParse(fileList);
      setBatchResult(res);

      // 预填覆盖值：仅当所有文件识别一致、且不是「未知账户」时才默认带入
      const entities = [...new Set(res.files.map((f) => f.entity))];
      const accts = [...new Set(res.files.map((f) => f.account))];
      setOverrideEntity(entities.length === 1 ? entities[0] : undefined);
      setOverrideAccount(
        accts.length === 1 && accts[0] !== "未知账户" ? accts[0] : undefined
      );

      if (res.errors.length > 0) {
        res.errors.forEach((e) => message.warning(`${e.filename}: ${e.error}`));
      }
      if (res.total > 0) {
        message.success(`解析完成: ${res.files.length} 个文件, ${res.total} 条记录`);
        setStep(1);
      } else {
        message.error("所有文件解析失败");
      }
    } catch {
      message.error("上传解析失败");
    } finally {
      setProcessing(false);
    }
  };

  const handleConfirm = async () => {
    if (!batchResult) return;
    if (needsAccountOverride) {
      message.error("请先选择正确账户，再确认导入");
      return;
    }
    setConfirming(true);
    try {
      const res = await confirmImport(
        batchResult.records,
        overrideEntity || undefined,
        overrideAccount || undefined
      );
      setImportResult(res);
      message.success(`导入成功: ${res.imported} 条`);
      setStep(2);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "导入失败");
    } finally {
      setConfirming(false);
    }
  };

  const handleReset = () => {
    setStep(0);
    setBatchResult(null);
    setImportResult(null);
    setOverrideEntity(undefined);
    setOverrideAccount(undefined);
  };

  const previewColumns = [
    { title: "日期", dataIndex: "period", width: 100 },
    {
      title: "实体",
      dataIndex: "entity",
      width: 90,
      render: (v: string) => overrideEntity || v,
    },
    {
      title: "账户",
      dataIndex: "account",
      width: 130,
      ellipsis: true,
      render: (v: string) => {
        const acc = overrideAccount || v;
        return acc === "未知账户" ? <span style={{ color: "#f5222d" }}>{acc}</span> : acc;
      },
    },
    { title: "交易对方", dataIndex: "counterpart", width: 140, ellipsis: true },
    { title: "摘要", dataIndex: "abstract", width: 200, ellipsis: true },
    { title: "币种", dataIndex: "ccy", width: 55 },
    {
      title: "金额",
      dataIndex: "cf",
      width: 110,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? "#52c41a" : "#f5222d" }}>
          {v?.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    { title: "余额", dataIndex: "bal", width: 110, render: (v: number) => v?.toLocaleString() },
  ];

  return (
    <div>
      <Steps
        current={step}
        style={{ marginBottom: 24 }}
        items={[
          { title: "上传并解析" },
          { title: "预览确认" },
          { title: "完成" },
        ]}
      />

      {step === 0 && (
        <Spin spinning={processing} tip="正在上传并解析文件...">
          <Card>
            <Dragger
              accept=".xlsx,.xls"
              multiple
              showUploadList={false}
              beforeUpload={(_, fileList) => {
                handleFiles(fileList as unknown as File[]);
                return false;
              }}
              disabled={processing}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽上传银行流水文件（支持多个文件）</p>
              <p className="ant-upload-hint">
                支持 .xlsx / .xls 格式，自动识别银行类型（招商、中信、Airwallex、DBS）
              </p>
            </Dragger>
          </Card>
        </Spin>
      )}

      {step === 1 && batchResult && (
        <div>
          <Card
            title="解析结果"
            style={{ marginBottom: 16 }}
            extra={
              <Space>
                <Button onClick={handleReset}>重新选择</Button>
                <Button
                  type="primary"
                  loading={confirming}
                  disabled={needsAccountOverride}
                  onClick={handleConfirm}
                >
                  确认导入 ({batchResult.total} 条)
                </Button>
              </Space>
            }
          >
            <Space wrap style={{ marginBottom: 12 }}>
              {batchResult.files.map((f, i) => (
                <Tag
                  key={i}
                  color={BANK_COLORS[f.bank_type] || "default"}
                  style={{ padding: "4px 12px", fontSize: 13 }}
                >
                  {f.filename} → {f.bank_label} | {f.entity} | {f.account} | {f.count} 条
                </Tag>
              ))}
            </Space>
            {batchResult.errors.length > 0 && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
                message={`${batchResult.errors.length} 个文件解析失败`}
                description={batchResult.errors.map((e) => `${e.filename}: ${e.error}`).join("; ")}
              />
            )}
            {needsAccountOverride && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
                message="有文件未能自动识别账户（未知账户），请在下方手动指定账户后再导入"
              />
            )}
            <Space wrap align="end">
              <div>
                <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>覆盖实体（留空用自动识别）</div>
                <Select
                  allowClear
                  showSearch
                  style={{ width: 200 }}
                  placeholder="不覆盖"
                  value={overrideEntity}
                  onChange={setOverrideEntity}
                  options={entityOptions.map((e) => ({ value: e, label: e }))}
                />
              </div>
              <div>
                <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>覆盖账户（留空用自动识别）</div>
                <Select
                  allowClear
                  showSearch
                  style={{ width: 240 }}
                  placeholder="不覆盖"
                  value={overrideAccount}
                  onChange={setOverrideAccount}
                  options={accountOptions.map((a) => ({ value: a, label: a }))}
                />
              </div>
            </Space>
          </Card>

          <Card>
            <Table
              dataSource={batchResult.records.map((r, i) => ({ ...r, key: i }))}
              columns={previewColumns}
              size="small"
              scroll={{ x: 1000, y: 450 }}
              pagination={{ pageSize: 100, showTotal: (t) => `共 ${t} 条` }}
            />
          </Card>
        </div>
      )}

      {step === 2 && importResult && (
        <Result
          status="success"
          title="导入成功"
          subTitle={`批次: ${importResult.batch_id}`}
          extra={[
            <Button type="primary" key="again" onClick={handleReset}>
              继续导入
            </Button>,
          ]}
        >
          <Row gutter={24} style={{ marginTop: 16 }}>
            <Col span={6}>
              <Statistic title="导入条数" value={importResult.imported} />
            </Col>
            <Col span={6}>
              <Statistic title="重复跳过" value={importResult.duplicates} />
            </Col>
            <Col span={6}>
              <Statistic title="已分类" value={importResult.classified} valueStyle={{ color: "#52c41a" }} />
            </Col>
            <Col span={6}>
              <Statistic title="待分类" value={importResult.unclassified} valueStyle={{ color: "#faad14" }} />
            </Col>
          </Row>
        </Result>
      )}
    </div>
  );
}
