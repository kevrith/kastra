import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AppLayout from "./components/layout/AppLayout";

import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import AuthCallback from "./pages/auth/AuthCallback";
import ForgotPassword from "./pages/auth/ForgotPassword";
import ResetPassword from "./pages/auth/ResetPassword";
import AcceptInvite from "./pages/auth/AcceptInvite";
import Dashboard from "./pages/Dashboard";
import ClientList from "./pages/clients/ClientList";
import ClientDetail from "./pages/clients/ClientDetail";
import QuotationList from "./pages/quotations/QuotationList";
import QuotationForm from "./pages/quotations/QuotationForm";
import QuotationDetail from "./pages/quotations/QuotationDetail";
import Pipeline from "./pages/quotations/Pipeline";
import InvoiceList from "./pages/invoices/InvoiceList";
import InvoiceDetail from "./pages/invoices/InvoiceDetail";
import InvoiceCreate from "./pages/invoices/InvoiceCreate";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import TeamManagement from "./pages/TeamManagement";
import Expenses from "./pages/expenses/Expenses";
import Products from "./pages/products/Products";
import RecurringInvoices from "./pages/recurring/RecurringInvoices";
import ProjectPipeline from "./pages/projects/ProjectPipeline";
import ProjectDetail from "./pages/projects/ProjectDetail";
import PublicPayment from "./pages/pay/PublicPayment";
import PublicQuotation from "./pages/portal/PublicQuotation";
import ClientPortal from "./pages/portal/ClientPortal";
import PaystackVerify from "./pages/portal/PaystackVerify";
import SupplierPortal from "./pages/portal/SupplierPortal";
import Suppliers from "./pages/suppliers/Suppliers";
import NewSupplierRequest from "./pages/suppliers/NewSupplierRequest";
import SupplierRequestDetail from "./pages/suppliers/SupplierRequestDetail";
import Employees from "./pages/payroll/Employees";
import PayrollRuns from "./pages/payroll/PayrollRuns";
import PayrollRunDetail from "./pages/payroll/PayrollRunDetail";
import AuditLog from "./pages/AuditLog";
import PrivacyPolicy from "./pages/legal/PrivacyPolicy";
import TermsOfService from "./pages/legal/TermsOfService";
import Landing from "./pages/Landing";
import SuperAdmin from "./pages/superadmin/SuperAdmin";
import Spinner from "./components/ui/Spinner";

// Root route: Landing for visitors, dashboard for authenticated users
function RootRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex h-screen items-center justify-center"><Spinner size="lg" /></div>;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Landing />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Super admin — standalone, no app layout */}
          <Route path="/superadmin" element={<SuperAdmin />} />
          <Route path="/superadmin/*" element={<SuperAdmin />} />

          {/* Public */}
          <Route path="/" element={<RootRoute />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/auth/accept-invite" element={<AcceptInvite />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/pay/:invoiceId" element={<PublicPayment />} />
          <Route path="/portal/q/:quotationId" element={<PublicQuotation />} />
          <Route path="/portal/c/:token" element={<ClientPortal />} />
          <Route path="/portal/paystack/verify" element={<PaystackVerify />} />
          <Route path="/supplier-portal/:token" element={<SupplierPortal />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />

          {/* Protected app */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/clients" element={<ClientList />} />
            <Route path="/clients/:id" element={<ClientDetail />} />
            <Route path="/quotations" element={<QuotationList />} />
            <Route path="/quotations/pipeline" element={<Pipeline />} />
            <Route path="/quotations/new" element={<QuotationForm />} />
            <Route path="/quotations/:id" element={<QuotationDetail />} />
            <Route path="/quotations/:id/edit" element={<QuotationForm />} />
            <Route path="/invoices" element={<InvoiceList />} />
            <Route path="/invoices/new" element={<InvoiceCreate />} />
            <Route path="/invoices/:id" element={<InvoiceDetail />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/team" element={<TeamManagement />} />
            <Route path="/expenses" element={<Expenses />} />
            <Route path="/products" element={<Products />} />
            <Route path="/recurring" element={<RecurringInvoices />} />
            <Route path="/projects" element={<ProjectPipeline />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/suppliers/requests/new" element={<NewSupplierRequest />} />
            <Route path="/suppliers/requests/:id" element={<SupplierRequestDetail />} />
            <Route path="/employees" element={<Employees />} />
            <Route path="/payroll" element={<PayrollRuns />} />
            <Route path="/payroll/runs/:id" element={<PayrollRunDetail />} />
            <Route path="/audit-log" element={<AuditLog />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
