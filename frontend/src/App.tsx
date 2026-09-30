import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import ImportPage from "./pages/ImportPage";
import TransactionList from "./pages/TransactionList";
import ClassificationRulesPage from "./pages/ClassificationRules";
import CategoryTreePage from "./pages/CategoryTree";
import BankAccountsPage from "./pages/BankAccounts";
import ImportTemplatesPage from "./pages/ImportTemplates";
import MonthlyReportPage from "./pages/MonthlyReport";
import AmortizationPage from "./pages/AmortizationPage";
import CashBalancePage from "./pages/CashBalance";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/import" replace />} />
        <Route path="/import" element={<ImportPage />} />
        <Route path="/transactions" element={<TransactionList />} />
        <Route path="/report" element={<MonthlyReportPage />} />
        <Route path="/cash-balance" element={<CashBalancePage />} />
        <Route path="/amortization" element={<AmortizationPage />} />
        <Route path="/rules" element={<ClassificationRulesPage />} />
        <Route path="/categories" element={<CategoryTreePage />} />
        <Route path="/accounts" element={<BankAccountsPage />} />
        <Route path="/templates" element={<ImportTemplatesPage />} />
      </Route>
    </Routes>
  );
}
