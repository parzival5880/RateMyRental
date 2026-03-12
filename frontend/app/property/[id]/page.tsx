'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

interface PropertyData {
  property: Record<string, string | number>;
  evictions: Record<string, string>[];
  complaints: Record<string, string>[];
  reviews: Record<string, string | number | boolean>[];
  red_flag: { score: number; color: string };
  ai_summary: Record<string, unknown> | null;
}

function StarBar({ value }: { value: number }) {
  return (
    <span className="text-yellow-400 text-sm">
      {'★'.repeat(Math.round(value))}{'☆'.repeat(5 - Math.round(value))} {value}/5
    </span>
  );
}

const riskColors: Record<string, string> = {
  green: 'bg-green-900 border-green-700 text-green-300',
  yellow: 'bg-yellow-900 border-yellow-700 text-yellow-300',
  red: 'bg-red-900 border-red-700 text-red-300',
};

export default function PropertyPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<PropertyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiReport, setAiReport] = useState<Record<string, unknown> | null>(null);

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${API}/api/property/${id}`)
      .then(r => r.json())
      .then(d => {
        setData(d);
        if (d.ai_summary) setAiReport(d.ai_summary);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id]);

  const generateReport = async () => {
    setAiLoading(true);
    try {
      const r = await fetch(`${API}/api/property/${id}/ai-report`, { method: 'POST' });
      const d = await r.json();
      setAiReport(d);
    } catch {
      alert('AI service error. Make sure Ollama is running.');
    }
    setAiLoading(false);
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-gray-400 animate-pulse">Loading property data...</div>
    </div>
  );

  if (!data) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400">
      Property not found.
    </div>
  );

  const { property: p, evictions, complaints, reviews, red_flag } = data;
  const flagClass = riskColors[red_flag.color] || riskColors.green;
  const riskLabel = red_flag.color === 'green' ? '✓ Low Risk' : red_flag.color === 'yellow' ? '⚠ Medium Risk' : '✕ High Risk';

  return (
    <div className="min-h-screen bg-gray-950">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <Link href="/" className="text-white font-bold text-lg">RateMyRental</Link>
        <div className="flex gap-4 text-sm text-gray-400">
          <Link href="/lease-check" className="hover:text-white">AI Lease Check</Link>
          <Link href="/chat" className="hover:text-white">Chat</Link>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <h1 className="text-2xl font-bold text-white">{p.address}</h1>
        <p className="text-gray-400 text-sm mt-1">Dallas TX {p.zip}</p>
        <div className="flex flex-wrap gap-2 mt-3">
          <span className="bg-gray-800 border border-gray-700 text-gray-300 text-xs px-3 py-1 rounded-full">
            Owner: {p.owner_name || 'Unknown'}
          </span>
        </div>
        {p.owner_mailing_address && (
          <p className="text-gray-500 text-xs mt-1">Owner mailing: {p.owner_mailing_address}</p>
        )}

        {/* Risk badge */}
        <div className={`mt-4 border rounded-xl px-5 py-4 flex items-center gap-4 ${flagClass}`}>
          <span className="text-3xl font-bold">{red_flag.score}</span>
          <div>
            <div className="font-semibold text-lg">{riskLabel}</div>
            <div className="text-xs opacity-70">Risk score out of 100 · Based on evictions, complaints &amp; reviews</div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mt-4">
          {[
            { label: 'Eviction Filings', value: evictions.length, color: 'text-orange-400' },
            { label: '311 Complaints', value: complaints.length, color: 'text-yellow-400' },
            { label: 'Tenant Reviews', value: reviews.length, color: 'text-blue-400' },
          ].map(s => (
            <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
              <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-gray-500 text-xs mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* AI Report */}
        <div className="mt-4 bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">🤖</span>
            <span className="font-semibold text-white">AI Risk Report</span>
            <span className="bg-purple-900 text-purple-300 text-xs px-2 py-0.5 rounded-full">DeepSeek R1</span>
          </div>
          {aiLoading ? (
            <div className="text-center text-gray-400 py-4">
              <div className="animate-spin inline-block w-5 h-5 border-2 border-purple-400 border-t-transparent rounded-full mb-2"></div>
              <div className="text-sm">DeepSeek R1 is analyzing this property...</div>
            </div>
          ) : aiReport ? (
            <div>
              <p className="text-gray-300 text-sm leading-relaxed">{aiReport.summary as string}</p>
              {(aiReport.risk_factors as string[])?.length > 0 && (
                <div className="mt-3">
                  <p className="text-gray-500 text-xs mb-2">Risk Factors Identified:</p>
                  <ul className="space-y-1">
                    {(aiReport.risk_factors as string[]).map((f, i) => (
                      <li key={i} className="text-orange-300 text-xs flex items-start gap-2">
                        <span>⚠</span><span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <button onClick={generateReport} className="mt-3 text-gray-500 text-xs hover:text-gray-300 underline">
                Regenerate report
              </button>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-gray-500 text-sm mb-3">Generate an AI-powered analysis of this property using all available data.</p>
              <button onClick={generateReport}
                className="bg-purple-700 hover:bg-purple-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors">
                Generate AI Report
              </button>
            </div>
          )}
        </div>

        {/* Evictions */}
        {evictions.length > 0 && (
          <div className="mt-4 bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
              ⚖️ Eviction Filings ({evictions.length})
            </h2>
            <div className="space-y-2">
              {evictions.map((ev, i) => (
                <div key={i} className="border-t border-gray-800 pt-2 text-sm">
                  <span className="text-gray-300">{ev.plaintiff_name}</span>
                  <span className="text-gray-600 ml-2 text-xs">{ev.filing_date}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 311 Complaints */}
        {complaints.length > 0 && (
          <div className="mt-4 bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="font-semibold text-white mb-3">🏙 311 Complaints ({complaints.length})</h2>
            <div className="space-y-2">
              {complaints.slice(0, 10).map((c, i) => (
                <div key={i} className="border-t border-gray-800 pt-2 text-sm flex justify-between">
                  <span className="text-gray-300">{c.complaint_type}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === 'Closed' ? 'bg-gray-800 text-gray-500' : 'bg-yellow-900 text-yellow-400'}`}>
                    {c.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Reviews */}
        <div className="mt-4 bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-white flex items-center gap-2">⭐ Tenant Reviews ({reviews.length})</h2>
            <Link href={`/review/${id}`}
              className="bg-blue-700 hover:bg-blue-600 text-white text-xs px-4 py-2 rounded-lg transition-colors">
              Leave a Review
            </Link>
          </div>
          {reviews.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-4">No reviews yet — be the first tenant to share your experience.</p>
          ) : (
            <div className="space-y-4">
              {reviews.map((r, i) => (
                <div key={i} className="border-t border-gray-800 pt-4">
                  <div className="flex gap-4 text-xs text-gray-400 mb-1">
                    <span>Maintenance: <StarBar value={r.maintenance_score as number} /></span>
                    <span>Lease: <StarBar value={r.lease_fairness as number} /></span>
                    <span>Comm: <StarBar value={r.communication_score as number} /></span>
                  </div>
                  <div className="flex gap-2 mt-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${r.deposit_returned === 'yes' ? 'bg-green-900 text-green-400' : r.deposit_returned === 'partial' ? 'bg-yellow-900 text-yellow-400' : 'bg-red-900 text-red-400'}`}>
                      Deposit: {r.deposit_returned}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${r.would_rent_again ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'}`}>
                      {r.would_rent_again ? 'Would rent again' : 'Would not rent again'}
                    </span>
                  </div>
                  {r.comments && <p className="text-gray-400 text-sm mt-2">{r.comments as string}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
