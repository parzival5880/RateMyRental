'use client';
import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';

interface Property {
  id: string;
  address: string;
  city: string;
  zip: string;
  owner_name: string;
}

function SearchResults() {
  const params = useSearchParams();
  const router = useRouter();
  const q = params.get('q') || '';
  const [results, setResults] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState(q);

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!q) return;
    setLoading(true);
    fetch(`${API}/api/search?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(d => { setResults(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [q]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 3) router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <div className="min-h-screen bg-gray-950">
      <nav className="flex items-center gap-4 px-6 py-4 border-b border-gray-800">
        <Link href="/" className="text-white font-bold text-lg">RateMyRental</Link>
        <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-xl">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          />
          <button type="submit" className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm">Search</button>
        </form>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-gray-900 rounded-xl h-16 animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            <p className="text-gray-400 text-sm mb-4">{results.length} results for &ldquo;{q}&rdquo;</p>
            <div className="space-y-2">
              {results.map(p => (
                <Link key={p.id} href={`/property/${p.id}`}
                  className="block bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 hover:border-blue-600 hover:bg-gray-800 transition-all group">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="text-white font-medium group-hover:text-blue-400 transition-colors">{p.address}</div>
                      <div className="text-gray-500 text-xs mt-0.5">
                        Dallas TX {p.zip} · Owner: {p.owner_name || 'Unknown'}
                      </div>
                    </div>
                    <span className="text-gray-600 group-hover:text-blue-400 text-lg">→</span>
                  </div>
                </Link>
              ))}
              {results.length === 0 && (
                <div className="text-center text-gray-500 py-12">No results found. Try a different address or owner name.</div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-950" />}>
      <SearchResults />
    </Suspense>
  );
}
