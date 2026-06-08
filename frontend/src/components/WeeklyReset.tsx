import { useState, useEffect } from 'react';
import { Loader2, Calendar } from 'lucide-react';

interface MilestoneCard {
  hash: number;
  name: string;
  description: string;
  icon: string | null;
  milestoneType: number;
  activityName: string | null;
  endDate: string | null;
}

interface WeeklyResponse {
  milestones: MilestoneCard[];
  endDate: string | null;
}

function timeUntil(iso: string | null): string {
  if (!iso) return '';
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return 'Reset passed';
  const h = Math.floor(diff / 3_600_000);
  const d = Math.floor(h / 24);
  if (d > 0) return `Resets in ${d}d ${h % 24}h`;
  return `Resets in ${h}h`;
}

export function WeeklyReset() {
  const [data, setData] = useState<WeeklyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/weekly')
      .then(async r => {
        if (!r.ok) throw new Error(`Error ${r.status}`);
        return r.json() as Promise<WeeklyResponse>;
      })
      .then(setData)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load weekly data'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-3 py-16 justify-center text-slate-500">
        <Loader2 className="animate-spin" size={18} />
        <span className="font-rajdhani text-sm uppercase tracking-widest">Loading weekly reset…</span>
      </div>
    );
  }

  if (error) {
    return <p className="font-rajdhani text-sm text-red-400/70 py-12">{error}</p>;
  }

  if (!data || data.milestones.length === 0) {
    return (
      <p className="font-rajdhani text-sm text-slate-600 py-12 tracking-widest uppercase">
        No weekly data available.
      </p>
    );
  }

  const resetStr = timeUntil(data.endDate);

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <div className="flex items-baseline gap-3 mb-1">
          <h2 className="font-cinzel text-xl text-destiny-accent">This Week</h2>
          {resetStr && (
            <span className="font-rajdhani text-[10px] uppercase tracking-widest text-slate-600 flex items-center gap-1">
              <Calendar size={9} />
              {resetStr}
            </span>
          )}
        </div>
        <p className="font-inter text-xs text-slate-600">
          Active weekly milestones and featured activities.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-white/5">
        {data.milestones.map(m => (
          <div key={m.hash} className="bg-slate-900/70 p-4 flex gap-3">
            {m.icon ? (
              <img src={m.icon} alt="" className="w-10 h-10 shrink-0 object-contain opacity-80" />
            ) : (
              <div className="w-10 h-10 shrink-0 bg-white/5 flex items-center justify-center">
                <span className="text-slate-700 text-xs">?</span>
              </div>
            )}
            <div className="min-w-0">
              <p className="font-rajdhani font-semibold text-white text-sm tracking-wide leading-tight truncate">
                {m.name}
              </p>
              {m.activityName && (
                <p className="font-rajdhani text-[10px] text-destiny-accent/80 tracking-widest uppercase mt-0.5 truncate">
                  {m.activityName}
                </p>
              )}
              {m.description && (
                <p className="font-inter text-[10px] text-slate-500 mt-1 leading-snug line-clamp-2">
                  {m.description}
                </p>
              )}
              <span className={`inline-block mt-1.5 font-rajdhani text-[9px] uppercase tracking-widest px-1.5 py-0.5 ${
                m.milestoneType === 7
                  ? 'bg-destiny-accent/10 text-destiny-accent/70'
                  : 'bg-white/5 text-slate-600'
              }`}>
                {m.milestoneType === 7 ? 'Raid' : 'Weekly'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
