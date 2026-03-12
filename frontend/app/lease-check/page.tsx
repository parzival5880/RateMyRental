'use client';
import { useState } from 'react';
import Link from 'next/link';

const SAMPLE_LEASE = `LEASE AGREEMENT
This lease is automatically renewed for another 12-month term unless tenant provides 60-day written notice of intent to vacate. Tenant waives right to jury trial in any dispute with landlord. Landlord may enter premises at any time with or without notice for inspections. Late fee of $150 will be charged if rent is not received by the 2nd of the month. Tenant is responsible for all repairs under $500. Security deposit of $1500 is non-refundable. Tenant agrees to pay attorney fees in any legal dispute regardless of outcome.`;

interface RedFlag { clause: string; issue: string; severity: 'high' | 'medium' | 'low' }
interface ScanResult {
  red_flags: RedFlag[];
  missing_protections: string[];
  positive_clauses: string[];
  overall_verdict: string;
  tenant_friendliness_score: number;
}

const severityColor: Record<string, string> = {
  high: 'bg-red-900 border-red-700 text-red-300',
  medium: 'bg-yellow-900 border-yellow-700 text-yellow-300',
  low: 'bg-blue-900 border-blue-700 text-blue-300',
};

export default function LeaseCheckPage() {
  const [lease, setLease] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState('');

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const scan = async () => {
    if (lease.length < 100) { setError('Paste more of your lease (at least 100 characters)'); return; }
    setError('');
    setLoading(true);
    setResult(null);
    try {
      const r = await fetch(`${API}/api/lease/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lease_text: lease }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Scan failed');
      setResult(d);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Scan failed. Make sure the AI service is running.');
    }
    setLoading(false);
  };

  const scoreColor = (s: number) => s >= 7 ? 'text-green-400' : s >= 4 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="min-h-screen bg-gray-950">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Link href="/" className="text-white font-bold text-lg">RateMyRental</Link>
          <span className="text-gray-600">›</span>
          <span>AI Lease Scanner</span>
        </div>
        <Link href="/chat" className="text-gray-400 hover:text-white text-sm">Tenant Chat →</Link>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            📄 AI Lease Scanner
            <span className="bg-purple-900 text-purple-300 text-xs px-2 py-0.5 rounded-full font-normal">DeepSeek R1</span>
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Paste your lease text below. AI will find red flags, missing protections, and unfair clauses — in seconds.
          </p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400 text-sm">Paste Lease Text</span>
            <button onClick={() => setLease(SAMPLE_LEASE)}
              className="text-blue-400 hover:text-blue-300 text-xs transition-colors">
              Load sample lease →
            </button>
          </div>
          <textarea
            value={lease}
            onChange={e => setLease(e.target.value)}
            rows={8}
            placeholder="Paste your full lease agreement here... (or click 'Load sample lease' to try it out)"
            className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 resize-none"
          />
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>{lease.length.toLocaleString()} / 50,000 characters</span>
            <span>First 8,000 chars analyzed</span>
          </div>
        </div>

        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

        <button onClick={scan} disabled={loading}
          className="w-full bg-purple-700 hover:bg-purple-600 disabled:bg-gray-800 text-white py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 mb-6">
          {loading ? (
            <><div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" /> Analyzing lease...</>
          ) : 'Scan for Red Flags'}
        </button>

        {result && (
          <div className="space-y-5">
            {/* Verdict */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex gap-4 items-start">
              <div>
                <div className={`text-4xl font-bold ${scoreColor(result.tenant_friendliness_score)}`}>
                  {result.tenant_friendliness_score}/10
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Tenant-Friendly Score</div>
              </div>
              <div>
                <div className="text-white font-medium">Overall Verdict</div>
                <p className="text-gray-400 text-sm mt-1">{result.overall_verdict}</p>
              </div>
            </div>

            {/* Red Flags */}
            {result.red_flags.length > 0 && (
              <div>
                <h2 className="text-orange-400 font-semibold mb-3 flex items-center gap-2">
                  ⚠ Red Flags ({result.red_flags.length})
                </h2>
                <div className="space-y-2">
                  {result.red_flags.map((f, i) => (
                    <div key={i} className={`border rounded-xl p-4 ${severityColor[f.severity]}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold uppercase px-1.5 py-0.5 rounded bg-black/30">{f.severity}</span>
                      </div>
                      <p className="text-xs opacity-75 italic mb-1 border-l-2 border-current pl-2">&ldquo;{f.clause}&rdquo;</p>
                      <p className="text-sm font-medium">{f.issue}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Missing Protections */}
            {result.missing_protections.length > 0 && (
              <div>
                <h2 className="text-blue-400 font-semibold mb-3">🛡 Missing Protections</h2>
                <div className="space-y-2">
                  {result.missing_protections.map((m, i) => (
                    <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-gray-300 text-sm flex items-start gap-2">
                      <span className="text-gray-600">→</span> {m}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Positive Clauses */}
            {result.positive_clauses.length > 0 && (
              <div>
                <h2 className="text-green-400 font-semibold mb-3">✓ Positive Clauses</h2>
                <div className="space-y-2">
                  {result.positive_clauses.map((c, i) => (
                    <div key={i} className="bg-green-950 border border-green-900 rounded-lg px-4 py-3 text-green-300 text-sm flex items-start gap-2">
                      <span>✓</span> {c}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <p className="text-gray-600 text-xs text-center">
              ⚠ This AI analysis is for informational purposes only and is not legal advice. For serious lease issues, contact{' '}
              <a href="https://texaslawhelp.org" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">Texas Law Help</a>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
