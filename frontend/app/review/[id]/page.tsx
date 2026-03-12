'use client';
import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [maintenance, setMaintenance] = useState(3);
  const [fairness, setFairness] = useState(3);
  const [communication, setCommunication] = useState(3);
  const [deposit, setDeposit] = useState('yes');
  const [depositDays, setDepositDays] = useState('');
  const [wouldRent, setWouldRent] = useState(true);
  const [comments, setComments] = useState('');
  const [landlordName, setLandlordName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          property_id: id,
          landlord_name: landlordName || 'Unknown',
          maintenance_score: maintenance,
          deposit_returned: deposit,
          deposit_days: depositDays ? parseInt(depositDays) : null,
          lease_fairness: fairness,
          communication_score: communication,
          would_rent_again: wouldRent,
          comments: comments || null,
        }),
      });
      if (r.ok) {
        router.push(`/property/${id}`);
      } else {
        const err = await r.json();
        alert(err.detail || 'Submission failed');
      }
    } catch {
      alert('Network error');
    }
    setSubmitting(false);
  };

  const ScoreSlider = ({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) => (
    <div className="mb-5">
      <div className="flex justify-between text-sm mb-2">
        <span className="text-gray-300">{label}</span>
        <span className="text-yellow-400 font-medium">{'★'.repeat(value)}{'☆'.repeat(5 - value)} {value}/5</span>
      </div>
      <input type="range" min={1} max={5} value={value} onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-blue-500" />
      <div className="flex justify-between text-xs text-gray-600 mt-1">
        <span>Poor</span><span>Excellent</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-950">
      <nav className="flex items-center px-6 py-4 border-b border-gray-800">
        <Link href={`/property/${id}`} className="text-gray-400 hover:text-white text-sm mr-4">← Back</Link>
        <span className="text-white font-bold">Leave a Review</span>
      </nav>

      <div className="max-w-lg mx-auto px-4 py-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Landlord name */}
          <div>
            <label className="block text-gray-300 text-sm mb-2">Landlord / Property Manager Name</label>
            <input value={landlordName} onChange={e => setLandlordName(e.target.value)}
              placeholder="Optional — helps other renters"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500" />
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-white font-medium mb-4">Rate Your Experience</h2>
            <ScoreSlider label="Maintenance & Repairs" value={maintenance} onChange={setMaintenance} />
            <ScoreSlider label="Lease Fairness" value={fairness} onChange={setFairness} />
            <ScoreSlider label="Communication" value={communication} onChange={setCommunication} />
          </div>

          {/* Deposit */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-white font-medium mb-3">Security Deposit</h2>
            <div className="flex gap-2 mb-3">
              {['yes', 'partial', 'no'].map(opt => (
                <button key={opt} type="button" onClick={() => setDeposit(opt)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${deposit === opt
                    ? opt === 'yes' ? 'bg-green-800 border-green-600 text-green-300'
                      : opt === 'partial' ? 'bg-yellow-800 border-yellow-600 text-yellow-300'
                      : 'bg-red-900 border-red-700 text-red-300'
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'}`}>
                  {opt === 'yes' ? 'Returned' : opt === 'partial' ? 'Partial' : 'Kept'}
                </button>
              ))}
            </div>
            {deposit !== 'no' && (
              <div>
                <label className="text-gray-400 text-xs block mb-1">Days to return (Texas law: 30 days)</label>
                <input type="number" value={depositDays} onChange={e => setDepositDays(e.target.value)}
                  placeholder="e.g. 14"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
              </div>
            )}
          </div>

          {/* Would rent again */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between">
            <span className="text-white font-medium">Would you rent here again?</span>
            <div className="flex gap-2">
              {[true, false].map(val => (
                <button key={String(val)} type="button" onClick={() => setWouldRent(val)}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors ${wouldRent === val
                    ? val ? 'bg-green-800 border-green-600 text-green-300' : 'bg-red-900 border-red-700 text-red-300'
                    : 'bg-gray-800 border-gray-700 text-gray-400'}`}>
                  {val ? 'Yes' : 'No'}
                </button>
              ))}
            </div>
          </div>

          {/* Comments */}
          <div>
            <label className="block text-gray-300 text-sm mb-2">Comments (optional)</label>
            <textarea value={comments} onChange={e => setComments(e.target.value)}
              rows={4} placeholder="Share your experience to help other tenants..."
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500 resize-none" />
          </div>

          <button type="submit" disabled={submitting}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white py-3 rounded-xl font-medium transition-colors">
            {submitting ? 'Submitting...' : 'Submit Review'}
          </button>
          <p className="text-gray-600 text-xs text-center">Anonymous — your IP is hashed, never stored in plain text</p>
        </form>
      </div>
    </div>
  );
}
