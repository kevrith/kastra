import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function PrivacyPolicy() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 text-sm">
          <ArrowLeft size={16} /> Back
        </button>

        <div className="card p-8 space-y-6 text-sm text-gray-700 leading-relaxed">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Privacy Policy</h1>
            <p className="text-gray-400 text-xs mt-1">Effective: 1 January 2025 · Last updated: 1 January 2025</p>
          </div>

          <p>
            Kastra Enterprises ("Kastra", "we", "our") is committed to protecting your personal data in
            accordance with the <strong>Kenya Data Protection Act 2019 (No. 24 of 2019)</strong> and any
            regulations made thereunder. This policy explains what data we collect, why we collect it, how
            we use it, and your rights as a data subject.
          </p>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">1. Data Controller</h2>
            <p>
              Kastra Enterprises is the data controller. You may contact us regarding data matters at{" "}
              <a href="mailto:privacy@kastra.co.ke" className="text-green-600 hover:underline">privacy@kastra.co.ke</a>.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">2. Personal Data We Collect</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong>Account data:</strong> name, email address, business name, hashed password.</li>
              <li><strong>Business data:</strong> client names, phone numbers, email addresses, invoice and quotation records.</li>
              <li><strong>Payment data:</strong> M-Pesa receipt numbers, transaction amounts (no card data stored).</li>
              <li><strong>Usage data:</strong> IP addresses in audit logs, timestamps of key actions.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">3. Lawful Basis for Processing (Section 30, DPA 2019)</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong>Contract performance:</strong> processing needed to deliver the Kastra service you signed up for.</li>
              <li><strong>Consent:</strong> recorded at registration with timestamp, for marketing communications.</li>
              <li><strong>Legal obligation:</strong> financial records retained for 5 years per the Kenya Tax Procedures Act 2015.</li>
              <li><strong>Legitimate interest:</strong> security monitoring and fraud prevention.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">4. How We Use Your Data</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>Provide and improve the Kastra platform.</li>
              <li>Send transactional emails (invoices, payment confirmations, overdue reminders).</li>
              <li>Comply with KRA eTIMS tax-invoicing requirements.</li>
              <li>Detect and prevent fraudulent activity.</li>
              <li>Respond to support requests.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">5. Data Sharing &amp; Third-Party Processors</h2>
            <p>We do not sell your personal data. We share data only with trusted processors necessary to deliver the Service:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong>Safaricom (Kenya):</strong> M-Pesa STK Push payment initiation and confirmation. Receives phone number and invoice amount.</li>
              <li><strong>Paystack (Nigeria/International):</strong> Card payment processing for business subscriptions and client invoice payments. Receives transaction amount and payer email.</li>
              <li><strong>SendGrid / Twilio (USA):</strong> Transactional email delivery (invoices, receipts, reminders). Receives recipient email address and message content.</li>
              <li><strong>Africa's Talking (Kenya):</strong> SMS notifications (payment confirmations, invoice reminders). Receives client phone number and message content — only when the client has consented to SMS.</li>
              <li><strong>Cloudinary (USA / International CDN):</strong> Storage of business logos and project photos. Receives image files uploaded by your account.</li>
              <li><strong>Google (USA):</strong> Optional Google OAuth sign-in. Receives your Google account email and profile name if you choose to sign in with Google.</li>
              <li><strong>KRA (Kenya):</strong> eTIMS invoice submissions as required by law.</li>
              <li><strong>Sentry (USA):</strong> Anonymised error diagnostics. No personally identifiable information is transmitted (<code>send_default_pii=False</code>).</li>
            </ul>
            <p className="text-sm text-gray-500 mt-1">All processors are bound by data processing agreements and are required to process data only on our instructions.</p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">5a. International Data Transfers (Section 49, DPA 2019)</h2>
            <p>
              Some processors (SendGrid, Cloudinary, Google, Sentry) are based outside Kenya. Where personal data
              is transferred internationally, we rely on one or more of the following safeguards:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Standard Contractual Clauses (SCCs) approved by the relevant data protection authority.</li>
              <li>The recipient country's data protection framework has been assessed as providing adequate protection.</li>
              <li>Your explicit consent at the point of data collection (e.g. Google sign-in).</li>
            </ul>
            <p className="text-sm text-gray-500 mt-1">You may request details of the specific safeguards in place by emailing <a href="mailto:privacy@kastra.co.ke" className="text-green-600 hover:underline">privacy@kastra.co.ke</a>.</p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">6. Data Retention</h2>
            <p>
              Account profiles are retained while your account is active. Financial records (invoices,
              quotations, payment details) are retained for <strong>5 years</strong> from the transaction
              date in compliance with the Kenya Tax Procedures Act 2015. Upon account deletion, your
              personal identifiers are anonymised while financial records are preserved.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">7. Your Rights (Sections 26–28, DPA 2019)</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong>Right of access:</strong> request a copy of all personal data we hold about you.</li>
              <li><strong>Right to rectification:</strong> correct inaccurate or incomplete data.</li>
              <li><strong>Right to erasure:</strong> delete your account; PII is anonymised within 30 days.</li>
              <li><strong>Right to data portability:</strong> export your data in JSON format from account settings.</li>
              <li><strong>Right to object:</strong> opt out of processing for marketing purposes.</li>
              <li><strong>Right to withdraw consent:</strong> withdraw at any time; this does not affect prior lawful processing.</li>
            </ul>
            <p>To exercise any right, email <a href="mailto:privacy@kastra.co.ke" className="text-green-600 hover:underline">privacy@kastra.co.ke</a> or use the settings in your account.</p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">8. Security (Section 41, DPA 2019)</h2>
            <p>
              We implement appropriate technical and organisational measures including: TLS encryption
              in transit, bcrypt password hashing, JWT with token versioning, OWASP security headers,
              IP-whitelisted payment callbacks, immutable audit logs, and regular vulnerability assessments.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">9. Cookies</h2>
            <p>
              We use a single HttpOnly, Secure, SameSite=Lax cookie to maintain your authenticated
              session. No third-party tracking cookies are used.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">10. Changes to This Policy</h2>
            <p>
              We will notify you by email at least 14 days before any material change. Continued use of
              Kastra after the effective date constitutes acceptance of the revised policy.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold text-gray-900">11. Complaints</h2>
            <p>
              You have the right to lodge a complaint with the{" "}
              <strong>Office of the Data Protection Commissioner (ODPC)</strong> of Kenya at{" "}
              <a href="https://www.odpc.go.ke" className="text-green-600 hover:underline" target="_blank" rel="noopener noreferrer">www.odpc.go.ke</a>.
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
