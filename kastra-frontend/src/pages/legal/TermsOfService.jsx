import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function TermsOfService() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 text-sm">
          <ArrowLeft size={16} /> Back
        </button>

        <div className="card p-8 space-y-6 text-sm text-gray-700 leading-relaxed">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Terms of Service</h1>
            <p className="text-gray-400 text-xs mt-1">Effective: 1 January 2025 · Last updated: 1 January 2025</p>
          </div>

          <p>
            By creating an account on Kastra you agree to these Terms of Service. Please read them carefully.
          </p>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">1. Service Description</h2>
            <p>
              Kastra provides cloud-based invoicing, quotation, and business-operations software for Kenyan
              small and medium enterprises. The service includes M-Pesa payment integration, KRA eTIMS
              compliance tools, and client management.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">2. Eligibility</h2>
            <p>
              You must be at least 18 years old and legally authorised to operate a business in Kenya.
              By registering, you represent that you meet these requirements.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">3. Account Responsibilities</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>You are responsible for maintaining the confidentiality of your login credentials.</li>
              <li>You must notify us immediately of any unauthorised use of your account.</li>
              <li>You are responsible for all activity that occurs under your account.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">4. Acceptable Use</h2>
            <p>You agree not to:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Use Kastra for any unlawful purpose or in violation of Kenyan law.</li>
              <li>Upload malicious code or attempt to compromise platform security.</li>
              <li>Reverse-engineer or copy any part of the service.</li>
              <li>Issue fraudulent invoices or misrepresent transactions.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">5. Intellectual Property</h2>
            <p>
              All platform software, design, and branding is owned by Kastra Enterprises. Your business
              data (clients, invoices, quotations) remains your property.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">6. Payment and Billing</h2>
            <p>
              Subscription fees (if applicable) are billed in advance. Refunds are assessed on a
              case-by-case basis. We reserve the right to suspend accounts with overdue balances.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">7. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by Kenyan law, Kastra shall not be liable for indirect,
              incidental, or consequential damages arising from use of the service. Our total liability
              shall not exceed the amount you paid in the preceding 12 months.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">8. Termination</h2>
            <p>
              You may cancel your account at any time from account settings. We may suspend or terminate
              accounts that violate these terms. Upon termination, your data is handled per our{" "}
              <a href="/privacy" className="text-green-600 hover:underline">Privacy Policy</a>.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">9. Governing Law</h2>
            <p>
              These Terms are governed by the laws of Kenya. Any dispute shall be resolved in the courts
              of Nairobi, Kenya.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">10. Contact</h2>
            <p>
              Questions about these Terms? Email{" "}
              <a href="mailto:legal@kastra.co.ke" className="text-green-600 hover:underline">legal@kastra.co.ke</a>.
            </p>
          </section>

          <p className="text-xs text-gray-400 border-t pt-4">
            © {new Date().getFullYear()} Kastra Enterprises. Registered in Kenya.
          </p>
        </div>
      </div>
    </div>
  );
}
