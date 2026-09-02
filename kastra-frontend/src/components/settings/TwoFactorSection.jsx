import { useEffect, useState } from "react";
import { ShieldCheck, Loader, Copy, Check } from "lucide-react";
import {
  twoFactorStatus, twoFactorSetup, twoFactorEnable, twoFactorDisable,
} from "../../api/auth";

/**
 * Two-factor authentication panel.
 *
 * Three states: off (offer setup), setting-up (QR + confirm code), on (recovery
 * code count + disable). Recovery codes come back exactly once, at enable time,
 * so they live in component state and are flagged as the only chance to save them.
 */
export default function TwoFactorSection({ Section }) {
  const [status, setStatus] = useState(null);
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState("");
  const [backupCodes, setBackupCodes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [password, setPassword] = useState("");

  const load = () => twoFactorStatus().then(({ data }) => setStatus(data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const startSetup = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await twoFactorSetup();
      setSetup(data);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not start setup");
    } finally { setBusy(false); }
  };

  const confirmSetup = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await twoFactorEnable(code);
      setBackupCodes(data.backup_codes);
      setSetup(null); setCode("");
      await load();
    } catch (err) {
      setError(err.response?.data?.detail ?? "That code is not valid");
    } finally { setBusy(false); }
  };

  const handleDisable = async () => {
    setBusy(true); setError("");
    try {
      await twoFactorDisable(password);
      setPassword(""); setDisabling(false); setBackupCodes(null);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not disable");
    } finally { setBusy(false); }
  };

  const copyCodes = () => {
    navigator.clipboard?.writeText(backupCodes.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!status) return null;

  return (
    <Section title="Two-Factor Authentication" icon={ShieldCheck}>
      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

      {backupCodes && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-3">
          <p className="text-sm font-semibold text-amber-900">
            Save these recovery codes now — they are shown only once.
          </p>
          <p className="text-xs text-amber-800">
            Each works a single time, for signing in if you lose your phone.
          </p>
          <div className="grid grid-cols-2 gap-2 font-mono text-sm text-gray-800">
            {backupCodes.map((c) => <div key={c} className="bg-white rounded px-2 py-1 text-center">{c}</div>)}
          </div>
          <button className="btn-secondary text-xs inline-flex items-center gap-1.5" onClick={copyCodes}>
            {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy all"}
          </button>
        </div>
      )}

      {!status.enabled && !setup && (
        <>
          <p className="text-sm text-gray-500">
            Require a code from your phone in addition to your password. Strongly recommended —
            this account can view invoices and move money.
          </p>
          <div className="flex justify-end">
            <button className="btn-primary inline-flex items-center gap-2" onClick={startSetup} disabled={busy}>
              {busy && <Loader size={15} className="animate-spin" />} Set up two-factor
            </button>
          </div>
        </>
      )}

      {setup && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Scan this with Google Authenticator, Authy, or any TOTP app, then enter the 6-digit code it shows.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 items-center sm:items-start">
            <img src={setup.qr_data_uri} alt="Two-factor QR code" className="w-40 h-40 border border-gray-200 rounded-lg" />
            <div className="flex-1 space-y-3 w-full">
              <div>
                <label className="label">Can&apos;t scan? Enter this key manually</label>
                <code className="block bg-gray-50 border border-gray-200 rounded px-2 py-1.5 text-xs break-all">{setup.secret}</code>
              </div>
              <div>
                <label className="label">6-digit code</label>
                <input
                  className="input text-center text-lg tracking-[0.3em] font-mono"
                  inputMode="numeric" maxLength={6} placeholder="000000"
                  value={code} onChange={(e) => setCode(e.target.value)}
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button className="btn-secondary" onClick={() => { setSetup(null); setCode(""); setError(""); }}>Cancel</button>
                <button className="btn-primary" onClick={confirmSetup} disabled={busy || code.length < 6}>
                  {busy ? "Verifying…" : "Turn on"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {status.enabled && !setup && (
        <>
          <div className="flex items-center gap-2 text-sm">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700">On</span>
            <span className="text-gray-500">
              {status.backup_codes_remaining} recovery code{status.backup_codes_remaining === 1 ? "" : "s"} left
            </span>
          </div>
          {!disabling ? (
            <div className="flex justify-end">
              <button className="btn-secondary text-red-600" onClick={() => setDisabling(true)}>Turn off</button>
            </div>
          ) : (
            <div className="space-y-3 border-t border-gray-100 pt-3">
              <div>
                <label className="label">Confirm your password to turn 2FA off</label>
                <input className="input" type="password" value={password}
                  onChange={(e) => setPassword(e.target.value)} />
              </div>
              <div className="flex gap-2 justify-end">
                <button className="btn-secondary" onClick={() => { setDisabling(false); setPassword(""); setError(""); }}>Cancel</button>
                <button className="btn-primary bg-red-600 hover:bg-red-700" onClick={handleDisable} disabled={busy || !password}>
                  {busy ? "Turning off…" : "Turn off"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </Section>
  );
}
