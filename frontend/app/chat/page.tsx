'use client';
import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';

interface Message {
  role: 'user' | 'ai';
  content: string;
}

const SUGGESTIONS = [
  'Can my landlord keep my deposit for normal wear and tear?',
  'My landlord won\'t fix my AC — what can I do?',
  'How much notice does my landlord need to enter?',
  'What\'s the eviction process in Dallas?',
  'Can my landlord raise my rent during my lease?',
  'Is my landlord required to fix mold?',
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: 'Hi! I\'m your Dallas tenant rights assistant. I can help with questions about deposits, repairs, evictions, lease rights, and more. What\'s on your mind?' },
  ]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (question: string) => {
    if (!question.trim() || streaming) return;
    const q = question.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setStreaming(true);

    // Add empty AI message that we'll fill in
    setMessages(prev => [...prev, { role: 'ai', content: '' }]);

    try {
      const response = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });

      if (!response.body) throw new Error('No stream');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') break;
          try {
            const chunk = JSON.parse(data);
            if (chunk.text) {
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: 'ai',
                  content: updated[updated.length - 1].content + chunk.text,
                };
                return updated;
              });
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'ai', content: 'Sorry, the AI service is unavailable. Make sure Ollama is running: `ollama serve`' };
        return updated;
      });
    }
    setStreaming(false);
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-white font-bold text-lg">RateMyRental</Link>
          <span className="text-gray-600">›</span>
          <span className="text-gray-300 text-sm">Tenant Rights Chat</span>
          <span className="bg-green-900 text-green-400 text-xs px-2 py-0.5 rounded-full">DeepSeek R1 · Dallas Law</span>
        </div>
        <Link href="/lease-check" className="text-gray-400 hover:text-white text-sm">Lease Scanner →</Link>
      </nav>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} items-start gap-2`}>
              {m.role === 'ai' && (
                <div className="w-7 h-7 rounded-full bg-green-800 flex items-center justify-center text-xs flex-shrink-0 mt-1">🏠</div>
              )}
              <div className={`max-w-lg rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-sm'
                  : 'bg-gray-900 border border-gray-800 text-gray-200 rounded-tl-sm'
              }`}>
                {m.content === '' && m.role === 'ai' ? (
                  <div className="flex gap-1 py-1">
                    {[0, 150, 300].map(d => (
                      <div key={d} className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                        style={{ animationDelay: `${d}ms` }} />
                    ))}
                  </div>
                ) : (
                  m.content
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Suggestion chips */}
      {messages.length <= 2 && !streaming && (
        <div className="px-4 pb-2">
          <div className="max-w-2xl mx-auto flex flex-wrap gap-2">
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => send(s)}
                className="bg-gray-900 hover:bg-gray-800 border border-gray-700 text-gray-400 hover:text-white text-xs px-3 py-1.5 rounded-full transition-colors">
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-800 px-4 py-4">
        <div className="max-w-2xl mx-auto flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send(input)}
            placeholder="Ask anything about your tenant rights in Dallas..."
            disabled={streaming}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-green-500 disabled:opacity-50"
          />
          <button onClick={() => send(input)} disabled={streaming || !input.trim()}
            className="bg-green-700 hover:bg-green-600 disabled:bg-gray-800 text-white px-5 py-3 rounded-xl text-sm font-medium transition-colors">
            Send
          </button>
        </div>
        <p className="text-gray-700 text-xs text-center mt-2">
          Not legal advice. For serious issues contact <a href="tel:2147481234" className="text-gray-500">Dallas Legal Aid: 214-748-1234</a>
        </p>
      </div>
    </div>
  );
}
