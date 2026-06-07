import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export function Home() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) navigate('/dashboard');
  }, [isAuthenticated, navigate]);

  const handleLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('/auth/login');
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      if (!data.auth_url) throw new Error('No auth_url in response');
      window.location.href = data.auth_url;
    } catch (err: any) {
      setError(err.message ?? 'Could not reach backend — is it running?');
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-center px-4">
      <div className="max-w-2xl w-full">
        <h1
          className="text-5xl md:text-7xl font-bold tracking-widest text-destiny-accent mb-4 uppercase"
          style={{ textShadow: '0 0 20px rgba(212, 175, 55, 0.3)' }}
        >
          OrbitOps
        </h1>
        <p className="text-lg text-slate-400 mb-12 max-w-lg mx-auto">
          Tactical fireteam analysis, lore decryption, and Vanguard logistics for guardians operating in deep cover.
        </p>

        <button
          onClick={handleLogin}
          disabled={loading}
          className="group relative inline-flex items-center justify-center px-8 py-4 font-bold text-white uppercase tracking-widest bg-slate-900 border border-slate-700 hover:border-destiny-accent transition-all duration-300 overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div className="absolute inset-0 bg-destiny-accent/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out" />
          <span className="relative">{loading ? 'Connecting...' : 'Authorize via Bungie.net'}</span>
        </button>

        {error && (
          <p className="mt-4 text-sm text-red-400">{error}</p>
        )}

        <div className="mt-16 pt-8 border-t border-slate-800/50 flex flex-col items-center">
          <p className="text-sm text-slate-500 mb-4">Or proceed without vanguard authorization</p>
          <Link to="/theorycraft" className="text-sm text-slate-400 hover:text-destiny-accent transition-colors">
            Enter Theory-craft Mode &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}
