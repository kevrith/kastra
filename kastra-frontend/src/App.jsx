import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AppLayout from "./components/layout/AppLayout";
import Landing from "./pages/Landing";
import Spinner from "./components/ui/Spinner";

const Login = lazy(() => import("./pages/auth/Login"));
const Register = lazy(() => import("./pages/auth/Register"));
const AuthCallback = lazy(() => import("./pages/auth/AuthCallback"));
const VerifyEmail = lazy(() => import("./pages/auth/VerifyEmail"));
const ForgotPassword = lazy(() => import("./pages/auth/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/auth/ResetPassword"));
const AcceptInvite = lazy(() => import("./pages/auth/AcceptInvite"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const ClientList = lazy(() => import("./pages/clients/ClientList"));
const ClientDetail = lazy(() => import("./pages/clients/ClientDetail"));
const QuotationList = lazy(() => import("./pages/quotations/QuotationList"));
const QuotationForm = lazy(() => import("./pages/quotations/QuotationForm"));
const QuotationDetail = lazy(() => import("./pages/quotations/QuotationDetail"));
const Pipeline = lazy(() => import("./pages/quotations/Pipeline"));
const InvoiceList = lazy(() => import("./pages/invoices/InvoiceList"));
const InvoiceDetail = lazy(() => import("./pages/invoices/InvoiceDetail"));
const InvoiceCreate = lazy(() => import("./pages/invoices/InvoiceCreate"));
const Reconciliation = lazy(() => import("./pages/invoices/Reconciliation"));
const Reports = lazy(() => import("./pages/Reports"));
const Settings = lazy(() => import("./pages/Settings"));
const TeamManagement = lazy(() => import("./pages/TeamManagement"));
const Expenses = lazy(() => import("./pages/expenses/Expenses"));
const Products = lazy(() => import("./pages/products/Products"));
const RecurringInvoices = lazy(() => import("./pages/recurring/RecurringInvoices"));
const ProjectPipeline = lazy(() => import("./pages/projects/ProjectPipeline"));
const ProjectDetail = lazy(() => import("./pages/projects/ProjectDetail"));
const PublicPayment = lazy(() => import("./pages/pay/PublicPayment"));
const PublicQuotation = lazy(() => import("./pages/portal/PublicQuotation"));
const ClientPortal = lazy(() => import("./pages/portal/ClientPortal"));
const PaystackVerify = lazy(() => import("./pages/portal/PaystackVerify"));
const SupplierPortal = lazy(() => import("./pages/portal/SupplierPortal"));
const SupplierOrderPortal = lazy(() => import("./pages/portal/SupplierOrderPortal"));
const Suppliers = lazy(() => import("./pages/suppliers/Suppliers"));
const NewSupplierRequest = lazy(() => import("./pages/suppliers/NewSupplierRequest"));
const SupplierRequestDetail = lazy(() => import("./pages/suppliers/SupplierRequestDetail"));
const PurchaseOrders = lazy(() => import("./pages/purchasing/PurchaseOrders"));
const PurchaseOrderForm = lazy(() => import("./pages/purchasing/PurchaseOrderForm"));
const PurchaseOrderDetail = lazy(() => import("./pages/purchasing/PurchaseOrderDetail"));
const SupplierBills = lazy(() => import("./pages/purchasing/SupplierBills"));
const Employees = lazy(() => import("./pages/payroll/Employees"));
const PayrollRuns = lazy(() => import("./pages/payroll/PayrollRuns"));
const PayrollRunDetail = lazy(() => import("./pages/payroll/PayrollRunDetail"));
const AuditLog = lazy(() => import("./pages/AuditLog"));
const PrivacyPolicy = lazy(() => import("./pages/legal/PrivacyPolicy"));
const TermsOfService = lazy(() => import("./pages/legal/TermsOfService"));
const Docs = lazy(() => import("./pages/Docs"));
const Help = lazy(() => import("./pages/Help"));
const SuperAdmin = lazy(() => import("./pages/superadmin/SuperAdmin"));
const TestimonialForm = lazy(() => import("./pages/TestimonialForm"));
const AffiliateRegister = lazy(() => import("./pages/affiliate/AffiliateRegister"));
const AffiliateLogin = lazy(() => import("./pages/affiliate/AffiliateLogin"));
const AffiliateDashboard = lazy(() => import("./pages/affiliate/AffiliateDashboard"));

function FullScreenSpinner() {
  return <div className="flex h-screen items-center justify-center"><Spinner size="lg" /></div>;
}

// Root route: Landing for visitors, dashboard for authenticated users
function RootRoute() {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenSpinner />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Landing />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<FullScreenSpinner />}>
          <Routes>
            {/* Super admin — standalone, no app layout */}
            <Route path="/superadmin/*" element={<SuperAdmin />} />

            {/* Affiliate portal — standalone */}
            <Route path="/affiliate/register" element={<AffiliateRegister />} />
            <Route path="/affiliate/login" element={<AffiliateLogin />} />
            <Route path="/affiliate/dashboard" element={<AffiliateDashboard />} />

            {/* Public */}
            <Route path="/" element={<RootRoute />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/auth/accept-invite" element={<AcceptInvite />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/pay/:invoiceId" element={<PublicPayment />} />
            <Route path="/portal/q/:quotationId" element={<PublicQuotation />} />
            <Route path="/portal/c/:token" element={<ClientPortal />} />
            <Route path="/portal/paystack/verify" element={<PaystackVerify />} />
            <Route path="/supplier-portal/:token" element={<SupplierPortal />} />
            <Route path="/supplier-order/:token" element={<SupplierOrderPortal />} />
            <Route path="/testimonial/:token" element={<TestimonialForm />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/terms" element={<TermsOfService />} />
            <Route path="/docs" element={<Docs />} />

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
              <Route path="/reconciliation" element={<Reconciliation />} />
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
              <Route path="/purchase-orders" element={<PurchaseOrders />} />
              <Route path="/purchase-orders/new" element={<PurchaseOrderForm />} />
              <Route path="/purchase-orders/:id" element={<PurchaseOrderDetail />} />
              <Route path="/purchase-orders/:id/edit" element={<PurchaseOrderForm />} />
              <Route path="/supplier-bills" element={<SupplierBills />} />
              <Route path="/employees" element={<Employees />} />
              <Route path="/payroll" element={<PayrollRuns />} />
              <Route path="/payroll/runs/:id" element={<PayrollRunDetail />} />
              <Route path="/audit-log" element={<AuditLog />} />
              <Route path="/help" element={<Help />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
