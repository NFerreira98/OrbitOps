import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const setAuth = useAuthStore((s) => s.setAuth);
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    const code = searchParams.get('code');
    if (!code) {
      setError('No authorization code in URL.');
      return;
    }

    const exchangeToken = async () => {
      try {
        const res = await fetch(`/auth/token?code=${code}`, {
          method: 'POST',
        });
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Token exchange failed: ${body}`);
        }
        const data = await res.json();
        setAuth({
          accessToken: data.access_token,
          displayName: data.display_name,
          primaryMembership: data.primary_membership,
          allMemberships: data.destiny_memberships ?? [],
        });
        navigate('/dashboard');
      } catch (err: any) {
        setError(err.message ?? 'Unknown error during authentication.');
      }
    };

    exchangeToken();
  }, [searchParams, navigate, setAuth]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-red-400">
        <h2 className="text-xl font-bold mb-2">Authentication Failed</h2>
        <p className="text-sm text-red-300 mb-4 max-w-sm text-center">{error}</p>
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 bg-slate-800 text-white hover:bg-slate-700 transition"
        >
          Return Home
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-slate-300">
      <Loader2 className="w-12 h-12 animate-spin mb-4 text-destiny-accent" />
      <h2 className="text-xl">Transmatting Data...</h2>
      <p className="mt-2 text-slate-500">Securing connection to the Vanguard networks.</p>
    </div>
  );
}
