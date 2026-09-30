export interface Transaction {
  id: number;
  entity: string;
  account: string;
  counterpart: string | null;
  period: string;
  abstract: string | null;
  ccy: string;
  cf: number;
  bal: number | null;
  note: string | null;
  exchange_rate: number;
  cf_in_cny: number | null;
  management: string | null;
  grouping: string | null;
  class_name: string | null;
  cf_line: string | null;
  classification_method: string | null;
  classification_confidence: number | null;
  import_batch: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  sum_cf: number;
  sum_cf_in_cny: number;
}

export interface TransactionUpdate {
  entity?: string;
  account?: string;
  counterpart?: string;
  period?: string;
  abstract?: string;
  ccy?: string;
  cf?: number;
  bal?: number;
  note?: string;
  management?: string;
  grouping?: string;
  class_name?: string;
  cf_line?: string;
  classification_method?: string;
}

export interface BulkUpdateRequest {
  ids: number[];
  entity?: string;
  account?: string;
  management?: string;
  grouping?: string;
  class_name?: string;
  cf_line?: string;
  classification_method?: string;
}

export interface BankAccount {
  id: number;
  entity: string;
  account: string;
  account_number: string | null;
  ccy: string;
  bank_type: string | null;
  created_at: string | null;
}

export interface CategoryNode {
  id: number;
  name: string;
  level: number;
  parent_id: number | null;
  cf_line: string | null;
  sort_order: number;
  children: CategoryNode[];
}

export interface CategoryLookup {
  management: string;
  class_name: string | null;
  grouping: string | null;
  cf_line: string | null;
}

export interface ClassificationRule {
  id: number;
  keyword: string;
  management: string;
  grouping: string;
  class_name: string;
  cf_line: string | null;
  source: string;
  match_count: number;
  confidence: number;
  created_at: string | null;
}

export interface ImportTemplate {
  id: number;
  name: string;
  bank_type: string;
  description: string | null;
  config: Record<string, unknown>;
  created_at: string | null;
}

export interface ExchangeRate {
  id: number;
  date: string;
  from_ccy: string;
  to_ccy: string;
  rate: number;
  source: string;
  created_at: string | null;
}

export interface ParseResponse {
  bank_type: string;
  entity: string;
  account: string;
  total: number;
  records: Record<string, unknown>[];
}

export interface ConfirmImportResponse {
  batch_id: string;
  imported: number;
  duplicates: number;
  classified: number;
  unclassified: number;
}

export interface UploadResponse {
  filename: string;
  saved_path: string;
  size: number;
}

// --- Amortization ---
export interface AmortizationEntry {
  id: number;
  amortization_id: number;
  period: string;
  amount: number;
  is_posted: boolean;
  debit_transaction_id: number | null;
  credit_transaction_id: number | null;
  created_at: string | null;
}

export interface Amortization {
  id: number;
  source_transaction_id: number | null;
  entity: string;
  total_amount: number;
  start_date: string;
  months: number;
  monthly_amount: number;
  prepaid_account: string;
  expense_account: string;
  grouping: string | null;
  class_name: string | null;
  status: string;
  posted_count: number;
  total_entries: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface AmortizationDetail extends Amortization {
  entries: AmortizationEntry[];
}

export interface AmortizationCreate {
  entity: string;
  total_amount: number;
  start_date: string;
  months: number;
  prepaid_account: string;
  expense_account: string;
  grouping?: string;
  class_name?: string;
  source_transaction_id?: number;
}

// --- Cash Balance ---
export interface CashBalanceAccount {
  account_id: number;
  entity: string;
  account: string;
  ccy: string;
  balance: number | null;
  balance_date: string | null;
  exchange_rate: number;
  balance_cny: number;
}

export interface CashBalanceResponse {
  date: string;
  accounts: CashBalanceAccount[];
  total_cny: number;
}

// --- Cash Balance Yearly ---
export interface MonthBalance {
  balance: number;
  balance_date: string;
  is_month_end: boolean;
  exchange_rate: number;
  balance_cny: number;
  transaction_id: number;
}

export interface CashBalanceYearlyAccount {
  account_id: number;
  entity: string;
  account: string;
  ccy: string;
  balances: Record<string, MonthBalance>;
}

export interface CashBalanceYearlyResponse {
  year: number;
  months: string[];
  accounts: CashBalanceYearlyAccount[];
  monthly_totals_cny: Record<string, number>;
  total_cny_latest: number;
}

