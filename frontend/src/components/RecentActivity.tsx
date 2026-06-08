import { useState, useEffect } from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

interface RecentEntry {
  instanceId: string;
  period: string;
  activityName: string;
  activityMode: number;
  modeLabel: string;
  completed: boolean;
  durationSecs: number;
  kills: number;
  deaths: number;
  assists: number;
}

interface RecentActivityProps {
  membershipType: number;
  membershipId: string;
  accessToken: string;
}

const MODE_COLORS: Record<string, string> = {
  Raid:       'text-destiny-accent',
  Dungeon:    'text-purple-400',
  Nightfall:  'text-blue-400',
  Strike:     'text-sky-400',
  Crucible:   'text-red-400',
  Gambit:     'text-green-400',
  Activity:   'text-slate-500',
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  if (d > 0) return `${d}d ago`;
  if (h > 0) return `${h}h ago`;
  return `${m}m ago`;
}

function fmtDur(secs: number): string {
  const m = Math.floor(secs / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  return `${m}m`;
}

export function RecentActivity({ membershipType, membershipId, accessToken }: RecentActivityProps) {
  const [entries, setEntries] = useState<RecentEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/recent?membership_type=${membershipType}&membership_id=${membershipId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(async r => {
        if (!r.ok) throw new Error(`Error ${r.status}`);
        const body = await r.json();
        return body.activities as RecentEntry[];
      })
      .then(setEntries)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [membershipType, membershipId, accessToken]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-slate-600 py-6">
        <Loader2 size={14} className="animate-spin" />
        <span className="font-rajdhani text-xs uppercase tracking-widest">Loading recent sessions…</span>
      </div>
    );
  }

  if (error || !entries?.length) return null;

  return (
    <div className="mt-10">
      <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
        Recent Sessions
      </p>
      <div className="border border-white/5 overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-white/5 bg-white/2">
              <th className="px-3 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600">Activity</th>
              <th className="px-2 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 text-right">When</th>
              <th className="px-2 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 text-right">Duration</th>
              <th className="px-2 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 text-right">K / D / A</th>
              <th className="px-2 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 text-center">Done</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(e => (
              <tr key={e.instanceId} className="border-b border-white/4 hover:bg-white/2 transition-colors">
                <td className="px-3 py-2">
                  <p className="font-rajdhani text-xs text-slate-200 leading-none truncate max-w-[180px]">
                    {e.activityName}
                  </p>
                  <p className={`font-rajdhani text-[9px] uppercase tracking-wide leading-none mt-0.5 ${MODE_COLORS[e.modeLabel] ?? 'text-slate-600'}`}>
                    {e.modeLabel}
                  </p>
                </td>
                <td className="px-2 py-2 text-right font-rajdhani text-[10px] text-slate-500 tabular-nums whitespace-nowrap">
                  {timeAgo(e.period)}
                </td>
                <td className="px-2 py-2 text-right font-rajdhani text-[10px] text-slate-500 tabular-nums">
                  {fmtDur(e.durationSecs)}
                </td>
                <td className="px-2 py-2 text-right font-rajdhani text-xs tabular-nums whitespace-nowrap">
                  <span className="text-white">{e.kills}</span>
                  <span className="text-slate-700"> / </span>
                  <span className="text-red-400/70">{e.deaths}</span>
                  <span className="text-slate-700"> / </span>
                  <span className="text-slate-500">{e.assists}</span>
                </td>
                <td className="px-2 py-2 text-center">
                  {e.completed
                    ? <CheckCircle size={12} className="text-green-500/60 inline" />
                    : <XCircle size={12} className="text-slate-700 inline" />
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
