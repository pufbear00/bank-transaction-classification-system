import axios from "axios";
import type {
  TransactionListResponse,
  Transaction,
  TransactionUpdate,
  BulkUpdateRequest,
  BankAccount,
  CategoryNode,
  CategoryLookup,
  ClassificationRule,
  ImportTemplate,
  ExchangeRate,
  ParseResponse,
  ConfirmImportResponse,
  UploadResponse,
  Amortization,
  AmortizationDetail,
  AmortizationCreate,
  CashBalanceResponse,
  CashBalanceYearlyResponse,
} from "../types";

const api = axios.create({ baseURL: "/api/v1" });

// --- Transactions ---
export async function listTransactions(
  params: Record<string, unknown>
): Promise<TransactionListResponse> {
  const { data } = await api.get("/transactions", { params });
  return data;
}

export async function createTransaction(
  payload: Record<string, unknown>
): Promise<Transaction> {
  const { data } = await api.post("/transactions", payload);
  return data;
}

export async function updateTransaction(
  id: number,
  update: TransactionUpdate
): Promise<Transaction> {
  const { data } = await api.put(`/transactions/${id}`, update);
  return data;
}

export async function bulkUpdateTransactions(
  req: BulkUpdateRequest
): Promise<{ updated: number }> {
  const { data } = await api.patch("/transactions/bulk", req);
  return data;
}

export async function exportTransactions(
  params: Record<string, unknown>
): Promise<Blob> {
  const { data } = await api.get("/transactions/export", {
    params,
    responseType: "blob",
  });
  return data;
}

export async function bulkDeleteTransactions(
  params: Record<string, unknown>
): Promise<{ deleted: number }> {
  const { data } = await api.delete("/transactions/bulk", { params });
  return data;
}

export async function fixExchangeRates(force = false): Promise<{ total: number; fixed: number }> {
  const { data } = await api.post(`/transactions/fix-exchange-rates?force=${force}`);
  return data;
}

export async function reclassifyTransactions(): Promise<{
  total_unclassified: number;
  classified: number;
  still_unclassified: number;
}> {
  const { data } = await api.post("/transactions/reclassify");
  return data;
}

// --- Import ---
export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/import/upload", form);
  return data;
}

export interface BatchParseResponse {
  files: { filename: string; bank_type: string; bank_label: string; entity: string; account: string; count: number }[];
  records: Record<string, unknown>[];
  total: number;
  errors: { filename: string; error: string }[];
}

export async function batchUploadAndParse(files: File[]): Promise<BatchParseResponse> {
  const form = new FormData();
  for (const f of files) {
    form.append("files", f);
  }
  const { data } = await api.post("/import/batch-parse", form);
  return data;
}

export async function parseFile(
  filePath: string,
  bankType?: string
): Promise<ParseResponse> {
  const form = new FormData();
  form.append("file_path", filePath);
  if (bankType) form.append("bank_type", bankType);
  const { data } = await api.post("/import/parse", form);
  return data;
}

export async function confirmImport(
  records: Record<string, unknown>[],
  entity?: string,
  account?: string
): Promise<ConfirmImportResponse> {
  const { data } = await api.post("/import/confirm", {
    records,
    entity,
    account,
  });
  return data;
}

// --- Categories ---
export async function getCategoryTree(): Promise<CategoryNode[]> {
  const { data } = await api.get("/categories");
  return data;
}

export async function getCategoriesFlat(
  level?: number
): Promise<CategoryNode[]> {
  const { data } = await api.get("/categories/flat", {
    params: level !== undefined ? { level } : {},
  });
  return data;
}

export async function lookupCategory(name: string): Promise<CategoryLookup> {
  const { data } = await api.get(`/categories/lookup/${encodeURIComponent(name)}`);
  return data;
}

export async function createCategory(
  body: Partial<CategoryNode>
): Promise<CategoryNode> {
  const { data } = await api.post("/categories", body);
  return data;
}

export async function updateCategory(
  id: number,
  body: Partial<CategoryNode>
): Promise<CategoryNode> {
  const { data } = await api.put(`/categories/${id}`, body);
  return data;
}

export async function deleteCategory(id: number): Promise<void> {
  await api.delete(`/categories/${id}`);
}

// --- Bank Accounts ---
export async function listBankAccounts(): Promise<BankAccount[]> {
  const { data } = await api.get("/bank-accounts");
  return data;
}

export async function createBankAccount(
  body: Partial<BankAccount>
): Promise<BankAccount> {
  const { data } = await api.post("/bank-accounts", body);
  return data;
}

export async function updateBankAccount(
  id: number,
  body: Partial<BankAccount>
): Promise<BankAccount> {
  const { data } = await api.put(`/bank-accounts/${id}`, body);
  return data;
}

export async function deleteBankAccount(id: number): Promise<void> {
  await api.delete(`/bank-accounts/${id}`);
}

// --- Classification Rules ---
export async function listRules(
  params?: Record<string, unknown>
): Promise<ClassificationRule[]> {
  const { data } = await api.get("/classification-rules", { params });
  return data;
}

export async function createRule(
  body: Partial<ClassificationRule>
): Promise<ClassificationRule> {
  const { data } = await api.post("/classification-rules", body);
  return data;
}

export async function updateRule(
  id: number,
  body: Partial<ClassificationRule>
): Promise<ClassificationRule> {
  const { data } = await api.put(`/classification-rules/${id}`, body);
  return data;
}

export async function deleteRule(id: number): Promise<void> {
  await api.delete(`/classification-rules/${id}`);
}

export async function exportRules(): Promise<Blob> {
  const { data } = await api.get("/classification-rules/export", { responseType: "blob" });
  return data;
}

export async function importRules(file: File): Promise<{ added: number; skipped: number }> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/classification-rules/import", form);
  return data;
}

// --- Import Templates ---
export async function listTemplates(): Promise<ImportTemplate[]> {
  const { data } = await api.get("/import-templates");
  return data;
}

export async function createTemplate(
  body: Partial<ImportTemplate>
): Promise<ImportTemplate> {
  const { data } = await api.post("/import-templates", body);
  return data;
}

export async function updateTemplate(
  id: number,
  body: Partial<ImportTemplate>
): Promise<ImportTemplate> {
  const { data } = await api.put(`/import-templates/${id}`, body);
  return data;
}

export async function deleteTemplate(id: number): Promise<void> {
  await api.delete(`/import-templates/${id}`);
}

// --- Exchange Rates ---
export async function listExchangeRates(
  params?: Record<string, unknown>
): Promise<ExchangeRate[]> {
  const { data } = await api.get("/exchange-rates", { params });
  return data;
}

export async function createExchangeRate(
  body: Partial<ExchangeRate>
): Promise<ExchangeRate> {
  const { data } = await api.post("/exchange-rates", body);
  return data;
}

export async function updateExchangeRate(
  id: number,
  body: Partial<ExchangeRate>
): Promise<ExchangeRate> {
  const { data } = await api.put(`/exchange-rates/${id}`, body);
  return data;
}

export async function deleteExchangeRate(id: number): Promise<void> {
  await api.delete(`/exchange-rates/${id}`);
}

// --- Reports ---
export interface MonthlySummaryItem {
  name: string;
  months: Record<string, number>;
  active_months: string[];
  total: number;
}

export interface MonthlySummaryClass extends MonthlySummaryItem {
  items: MonthlySummaryItem[];
}

export interface MonthlySummarySection extends MonthlySummaryItem {
  classes: MonthlySummaryClass[];
}

export interface MonthlySummaryResponse {
  year: number;
  months: string[];
  sections: MonthlySummarySection[];
  grand_total: { months: Record<string, number>; active_months: string[]; total: number };
  pnl_total?: { months: Record<string, number>; active_months: string[]; total: number };
  unclassified: { months: Record<string, number>; active_months: string[]; total: number };
}

export async function getMonthlySummary(
  params: Record<string, unknown>
): Promise<MonthlySummaryResponse> {
  const { data } = await api.get("/reports/monthly-summary", { params });
  return data;
}

export async function exportMonthlySummary(
  params: Record<string, unknown>
): Promise<Blob> {
  const { data } = await api.get("/reports/monthly-summary/export", {
    params,
    responseType: "blob",
  });
  return data;
}

// --- Cash Balance ---
export async function getCashBalance(
  params: { date?: string }
): Promise<CashBalanceResponse> {
  const { data } = await api.get("/reports/cash-balance", { params });
  return data;
}

export async function getCashBalanceYearly(
  params: { year: number }
): Promise<CashBalanceYearlyResponse> {
  const { data } = await api.get("/reports/cash-balance-yearly", { params });
  return data;
}

// --- Amortizations ---
export async function listAmortizations(): Promise<Amortization[]> {
  const { data } = await api.get("/amortizations");
  return data;
}

export async function createAmortization(
  body: AmortizationCreate
): Promise<AmortizationDetail> {
  const { data } = await api.post("/amortizations", body);
  return data;
}

export async function getAmortizationDetail(
  id: number
): Promise<AmortizationDetail> {
  const { data } = await api.get(`/amortizations/${id}`);
  return data;
}

export async function deleteAmortization(id: number): Promise<void> {
  await api.delete(`/amortizations/${id}`);
}
