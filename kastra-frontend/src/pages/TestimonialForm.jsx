import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Star, CheckCircle, AlertCircle, Loader } from "lucide-react";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function TestimonialForm() {
  const { token } = useParams();

  const [phase, setPhase] = useState("loading"); // loading | form | submitted | used | invalid
  const [, setPrefill] = useState({ name: "", role_hint: "" });
  const [form, setForm] = useState({ name: "", role: "", text: "", stars: 5, consent: false });
  const [hovered, setHovered] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API}/api/testimonials/form/${token}`)
      .then(async (r) => {
        if (r.status === 404) { setPhase("invalid"); return; }
        if (r.status === 410) {
          const body = await r.json().catch(() => ({}));
          setPhase(body.detail === "already_submitted" ? "used" : "invalid");
          return;
        }
        if (!r.ok) { setPhase("invalid"); return; }
        const data = await r.json();
        setPrefill(data);
        setForm((f) => ({ ...f, name: data.name, role: data.role_hint || "" }));
        setPhase("form");
      })
      .catch(() => setPhase("invalid"));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.consent) { setError("Please tick the consent checkbox to continue."); return; }
    if (!form.text.trim()) { setError("Please write something before submitting."); return; }
    setError("");
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/testimonials/form/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (r.status === 410) { setPhase("used"); return; }
      if (!r.ok) { const b = await r.json().catch(() => ({})); setError(b.detail ?? "Something went wrong."); return; }
      setPhase("submitted");
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (phase === "loading") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader size={28} className="text-green-600 animate-spin" />
      </div>
    );
  }

  if (phase === "invalid") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <AlertCircle size={40} className="text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-800 mb-2">Link not found</h2>
          <p className="text-gray-500 text-sm">This testimonial link is invalid or has expired. Please contact the team if you think this is a mistake.</p>
        </div>
      </div>
    );
  }

  if (phase === "used") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <CheckCircle size={40} className="text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-800 mb-2">Already submitted</h2>
          <p className="text-gray-500 text-sm">You've already shared your testimonial using this link. Thank you!</p>
        </div>
      </div>
    );
  }

  if (phase === "submitted") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <CheckCircle size={32} className="text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Thank you, {form.name.split(" ")[0]}!</h2>
          <p className="text-gray-500 leading-relaxed">
            Your testimonial has been received. Our team will review it shortly.
            If approved, it may be featured on the Kastra website.
          </p>
          <p className="text-xs text-gray-400 mt-6">Powered by Kastra · kastra.co.ke</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-start justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <img src="/kastra1.png" alt="Kastra" className="h-9 w-9 object-contain" />
            <span className="text-xl font-bold text-green-600">Kastra</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Share your experience</h1>
          <p className="text-gray-500 text-sm mt-2">
            Your honest feedback helps other Kenyan businesses discover Kastra.
            It only takes 2 minutes.
          </p>
        </div>

        <form onSubmit={submit} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-7 space-y-5">
          {/* Star rating */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">How would you rate Kastra?</label>
            <div className="flex gap-1.5">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onMouseEnter={() => setHovered(n)}
                  onMouseLeave={() => setHovered(0)}
                  onClick={() => setForm({ ...form, stars: n })}
                  className="focus:outline-none"
                >
                  <Star
                    size={32}
                    className={`transition-colors ${
                      n <= (hovered || form.stars)
                        ? "fill-amber-400 text-amber-400"
                        : "text-gray-300"
                    }`}
                  />
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-1">
              {["", "Poor", "Fair", "Good", "Great", "Excellent!"][(hovered || form.stars)]}
            </p>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your name</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              placeholder="Grace Wanjiku"
            />
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your title &amp; company</label>
            <input
              required
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
              placeholder="CEO, Wanjiku Consulting"
            />
          </div>

          {/* Testimonial text */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your testimonial
              <span className="font-normal text-gray-400 ml-1">(in your own words)</span>
            </label>
            <textarea
              required
              rows={5}
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 resize-none"
              placeholder="Tell us what you love about Kastra and how it has helped your business…"
            />
            <p className="text-xs text-gray-400 mt-1">{form.text.length} characters</p>
          </div>

          {/* Consent */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={form.consent}
              onChange={(e) => setForm({ ...form, consent: e.target.checked })}
              className="mt-0.5 accent-green-600 w-4 h-4 cursor-pointer"
            />
            <span className="text-sm text-gray-600 leading-relaxed group-hover:text-gray-800">
              I consent to Kastra publishing my name, title, and testimonial on their website and
              marketing materials. I confirm the feedback is genuine and reflects my own experience.
            </span>
          </label>

          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2.5 rounded-lg">
              <AlertCircle size={14} className="shrink-0" /> {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold py-3 rounded-xl text-sm transition"
          >
            {submitting ? "Submitting…" : "Submit testimonial"}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-5">
          Your submission is protected under the Kenya Data Protection Act 2019.
          You can request removal at any time by contacting Kastra.
        </p>
      </div>
    </div>
  );
}
