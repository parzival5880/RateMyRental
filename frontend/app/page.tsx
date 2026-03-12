'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function Home() {
  const [query, setQuery] = useState('');
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 3) router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <span className="text-white font-bold text-lg">RateMyRental</span>
        <div className="flex gap-4 text-sm text-gray-400">
          <Link href="/lease-check" className="hover:text-white transition-colors">AI Lease Check</Link>
          <Link href="/chat" className="hover:text-white transition-colors">Tenant Rights Chat</Link>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 text-center">
        <p className="text-xs tracking-widest text-blue-400 uppercase mb-4">Dallas Landlord Transparency</p>
        <h1 className="text-5xl font-bold text-white mb-3 leading-tight">
          Know Before You<br />
          <span className="text-blue-400">Sign the Lease</span>
        </h1>
        <p className="text-gray-400 text-lg mb-10 max-w-xl">
          Search any Dallas address or landlord name — get eviction history, city
          complaints, tenant reviews, and an AI risk report. All free. All public data.
        </p>

        <form onSubmit={handleSearch} className="flex gap-2 w-full max-w-xl">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Try: 5920 Forest Ln  or  Invitation Homes..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Search
          </button>
        </form>

        {/* Feature cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-14 w-full max-w-2xl">
          {[
            { icon: '🏠', title: 'Property Ownership', desc: '858K+ Dallas properties with owner names — including LLCs' },
            { icon: '⚖️', title: 'Eviction History', desc: 'Court filings data from Princeton Eviction Lab' },
            { icon: '🤖', title: 'AI Risk Report', desc: 'DeepSeek R1 analyzes all data and gives you a plain-English verdict' },
          ].map(c => (
            <div key={c.title} className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-left">
              <div className="text-2xl mb-2">{c.icon}</div>
              <div className="font-semibold text-white text-sm mb-1">{c.title}</div>
              <div className="text-gray-400 text-xs">{c.desc}</div>
            </div>
          ))}
        </div>

        <div className="flex gap-3 mt-8">
          <Link href="/lease-check"
            className="bg-purple-700 hover:bg-purple-600 text-white text-sm px-5 py-2.5 rounded-lg font-medium transition-colors flex items-center gap-2">
            📄 AI Lease Scanner
          </Link>
          <Link href="/chat"
            className="bg-green-800 hover:bg-green-700 text-white text-sm px-5 py-2.5 rounded-lg font-medium transition-colors flex items-center gap-2">
            💬 Tenant Rights Chat
          </Link>
        </div>
      </main>

      <footer className="text-center text-gray-600 text-xs py-4">
        Data: DCAD 2025 · Eviction Lab (Princeton) · Dallas Open Data · tenant reviews
      </footer>
    </div>
  );
}
