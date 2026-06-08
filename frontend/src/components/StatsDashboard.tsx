import { useState, useEffect, useRef } from 'react';
import { Loader2, ChevronUp, ChevronDown } from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, LabelList,
} from 'recharts';
import type { StatsDashboardResponse, ModeBlock, PvpStats, AbilityStats } from '../types/stats';

// ── Constants ────────────────────────────────────────────────────────────────

const EXPANSION_LINES = [
  { month: '2018-09', label: 'Forsaken' },
  { month: '2019-10', label: 'Shadowkeep' },
  { month: '2020-11', label: 'Beyond Light' },
  { month: '2022-02', label: 'Witch Queen' },
  { month: '2023-02', label: 'Lightfall' },
  { month: '2024-06', label: 'Final Shape' },
];

const MODE_COLORS: Record<string, string> = {
  pve:    '#3b82f6',
  pvp:    '#ef4444',
  gambit: '#22c55e',
};

const ERA_COLORS: Record<string, string> = {
  'Red War': '#ef4444', 'Forsaken': '#f97316', 'Shadowkeep': '#8b5cf6',
  'Beyond Light': '#3b82f6', 'Witch Queen': '#22c55e',
  'Lightfall': '#ec4899', 'The Final Shape': '#d4af37',
};

const MODE_LABELS: Record<string, string> = { raid: 'Raid', dungeon: 'Dungeon', strike: 'Strike', pvp: 'Crucible', gambit: 'Gambit', 'exotic-mission': 'Exotic Mission', misc: 'Other' };

function fmtMs(ms: number | null): string {
  if (!ms || ms <= 0) return '—';
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  return `${m}m ${s % 60}s`;
}

function fmtSecs(secs: number): string {
  if (!secs || secs <= 0) return '—';
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  if (m >= 60) return `${Math.floor(m / 60)}h ${m % 60}m`;
  return `${m}m ${s}s`;
}

const ABILITY_CATS: { key: keyof AbilityStats; pctKey: keyof AbilityStats; label: string; color: string }[] = [
  { key: 'gunKills',     pctKey: 'gunPct',     label: 'Guns',     color: '#d4af37' },
  { key: 'meleeKills',   pctKey: 'meleePct',   label: 'Melee',    color: '#f97316' },
  { key: 'grenadeKills', pctKey: 'grenadePct', label: 'Grenade',  color: '#22c55e' },
  { key: 'superKills',   pctKey: 'superPct',   label: 'Super',    color: '#8b5cf6' },
];

// ── AnimatedCounter ───────────────────────────────────────────────────────────

function AnimatedCounter({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [display, setDisplay] = useState(0);
  const start = useRef(performance.now());
  const duration = 1800;

  useEffect(() => {
    start.current = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const t = Math.min((now - start.current) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.floor(ease * target));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);

  return <>{display.toLocaleString()}{suffix}</>;
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function TimelineTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-white/10 px-3 py-2 text-xs font-rajdhani">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }} className="capitalize">
          {p.name}: <span className="text-white font-semibold">{p.value.toLocaleString()}</span>
        </p>
      ))}
    </div>
  );
}

// ── Crucible Career ───────────────────────────────────────────────────────────

function StatCell({ label, value, sub, accent = false }: { label: string; value: string | number; sub?: string; accent?: boolean }) {
  return (
    <div className="bg-slate-900/60 px-4 py-3">
      <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-0.5">{label}</p>
      <p className={`font-futura text-xl font-bold leading-none ${accent ? 'text-red-400' : 'text-white'}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </p>
      {sub && <p className="font-inter text-[10px] text-slate-700 mt-1 leading-tight">{sub}</p>}
    </div>
  );
}

function CrucibleCareer({ pvpStats: p }: { pvpStats: PvpStats }) {
  return (
    <div>
      <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
        Crucible Career · {p.activitiesEntered.toLocaleString()} Matches
      </p>

      {/* Core ratios */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/5 mb-px">
        <StatCell label="K/D Ratio"     value={p.kd.toFixed(2)}           sub={`${p.totalKills.toLocaleString()} kills · ${p.totalDeaths.toLocaleString()} deaths`} accent />
        <StatCell label="KDA"           value={p.kda.toFixed(2)}           sub={`${p.totalAssists.toLocaleString()} assists`} accent />
        <StatCell label="Win Rate"      value={`${p.winRate}%`}            sub={`${p.activitiesWon.toLocaleString()} wins`} accent />
        <StatCell label="Combat Rating" value={p.combatRating.toFixed(0)}  sub="" accent />
      </div>

      {/* Career records */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/5 mb-px">
        <StatCell label="Best Single Game"  value={p.bestSingleGameKills}         sub="kills in one match" />
        <StatCell label="Longest Spree"     value={p.longestKillSpree}            sub="consecutive kills" />
        <StatCell label="Longest Life"      value={fmtSecs(p.longestLifeSecs)}    sub="without dying" />
        <StatCell label="Precision %"       value={`${p.precisionPct}%`}          sub={`${p.precisionKills.toLocaleString()} headshots`} />
      </div>

      {/* Fireteam footprint */}
      <div className="grid grid-cols-3 gap-px bg-white/5">
        <StatCell label="Orbs Dropped"      value={p.orbsDropped}              sub="super energy for the team" />
        <StatCell label="Revives Given"     value={p.resurrectionsPerformed}   sub="teammates picked up" />
        <StatCell label="Revives Received"  value={p.resurrectionsReceived}    sub="times rescued" />
      </div>
    </div>
  );
}

// ── Ability DNA ───────────────────────────────────────────────────────────────

function AbilityDNA({ abilityStats: a }: { abilityStats: AbilityStats }) {
  return (
    <div>
      <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
        Ability DNA · How You Kill · {a.totalKills.toLocaleString()} total
      </p>

      {/* Stacked proportional bar */}
      <div className="flex h-5 overflow-hidden bg-white/5 mb-px rounded-none">
        {ABILITY_CATS.map(cat => {
          const pct = a[cat.pctKey] as number;
          return pct > 0 ? (
            <div key={cat.key} style={{ width: `${pct}%`, background: cat.color }}
              title={`${cat.label}: ${pct}%`} />
          ) : null;
        })}
      </div>

      {/* Per-category breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/5">
        {ABILITY_CATS.map(cat => {
          const kills = a[cat.key] as number;
          const pct   = a[cat.pctKey] as number;
          return (
            <div key={cat.key} className="bg-slate-900/60 px-4 py-3">
              <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
                style={{ background: cat.color }} />
              <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-0.5 mt-1">{cat.label}</p>
              <p className="font-futura text-xl font-bold text-white leading-none">{pct}%</p>
              <p className="font-inter text-[10px] text-slate-700 mt-1">{kills.toLocaleString()} kills</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface StatsDashboardProps {
  membershipType: number;
  membershipId: string;
  accessToken: string;
}

// ── Main component ────────────────────────────────────────────────────────────

export function StatsDashboard({ membershipType, membershipId, accessToken }: StatsDashboardProps) {
  const [data, setData] = useState<StatsDashboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<'completions' | 'kills' | 'fastestMs'>('completions');
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/api/stats/dashboard?membership_type=${membershipType}&membership_id=${membershipId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error((body as { detail?: string }).detail ?? `Error ${r.status}`);
        }
        return r.json() as Promise<StatsDashboardResponse>;
      })
      .then(setData)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load stats'))
      .finally(() => setLoading(false));
  }, [membershipType, membershipId, accessToken]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <Loader2 className="animate-spin text-destiny-accent" size={28} />
        <p className="font-rajdhani text-sm text-slate-500 tracking-widest uppercase">
          Building your 9-year timeline…
        </p>
        <p className="font-inter text-xs text-slate-700 max-w-xs">
          This takes about 10 seconds the first time. After that it's instant.
        </p>
        <div className="w-48 h-0.5 bg-white/5 overflow-hidden mt-2">
          <div className="h-full bg-destiny-accent/50 animate-pulse w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return <p className="font-rajdhani text-sm text-red-400/70 tracking-wide py-12">{error}</p>;
  }

  if (!data) return null;

  const { modes, timeline, topActivities, weaponBuckets, contextualStats, pvpStats, abilityStats } = data;

  const totalHours = modes.reduce((s, m) => s + m.hoursPlayed, 0);
  const totalKills = modes.reduce((s, m) => s + m.kills, 0);
  const totalActivities = modes.reduce((s, m) => s + m.activitiesEntered, 0);

  const filteredActivities = (activeMode
    ? topActivities.filter(a => a.mode === activeMode)
    : topActivities
  ).sort((a, b) => {
    const av = sortKey === 'fastestMs' ? (a.fastestMs ?? Infinity) : a[sortKey];
    const bv = sortKey === 'fastestMs' ? (b.fastestMs ?? Infinity) : b[sortKey];
    return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number);
  });

  const SortIcon = ({ k }: { k: typeof sortKey }) =>
    sortKey === k ? (sortDir === 'desc' ? <ChevronDown size={10} /> : <ChevronUp size={10} />) : null;

  const toggleSort = (k: typeof sortKey) => {
    if (sortKey === k) setSortDir(d => d === 'desc' ? 'asc' : 'desc');
    else { setSortKey(k); setSortDir(k === 'fastestMs' ? 'asc' : 'desc'); }
  };

  const pieData = modes.map(m => ({ ...m, fill: MODE_COLORS[m.mode] ?? '#64748b' }));

  return (
    <div className="space-y-8 max-w-4xl">

      {/* ── Hero Band ──────────────────────────────────────────────────────── */}
      <div>
        <h2 className="font-cinzel text-xl text-destiny-accent mb-1">By the Numbers</h2>
        <p className="font-inter text-xs text-slate-600 mb-5">
          Your complete Destiny 2 career — {timeline.length} months of history.
          {data.cached ? '' : ' Freshly computed and cached.'}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/5">
          {[
            { label: 'Hours Played', value: Math.round(totalHours), sub: contextualStats[0]?.frame },
            { label: 'Enemies Slain', value: totalKills, sub: contextualStats[1]?.frame },
            { label: 'Activities', value: totalActivities, sub: contextualStats[2]?.frame },
            { label: 'Primary Passion', value: modes.sort((a, b) => b.hoursPlayed - a.hoursPlayed)[0]?.hoursPlayed ?? 0, suffix: 'h', sub: contextualStats[3]?.frame },
          ].map(({ label, value, suffix, sub }) => (
            <div key={label} className="bg-slate-900/60 px-4 py-4">
              <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-1">{label}</p>
              <p className="font-futura text-2xl text-white font-bold leading-none">
                <AnimatedCounter target={value} suffix={suffix} />
              </p>
              {sub && <p className="font-inter text-[10px] text-slate-600 mt-1.5 leading-tight">{sub}</p>}
            </div>
          ))}
        </div>
      </div>

      {/* ── Signature Timeline ─────────────────────────────────────────────── */}
      <div>
        <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
          Activity History · Monthly
        </p>
        <div className="flex gap-4 mb-2">
          {Object.entries(MODE_COLORS).map(([k, color]) => (
            <span key={k} className="flex items-center gap-1.5 font-rajdhani text-[9px] uppercase tracking-widest text-slate-500">
              <span className="w-2 h-2 rounded-full" style={{ background: color }} />
              {k === 'pve' ? 'PvE' : k === 'pvp' ? 'PvP' : 'Gambit'}
            </span>
          ))}
        </div>
        <div className="bg-slate-900/40 border border-white/5 p-3">
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={timeline} margin={{ top: 16, right: 8, left: -28, bottom: 0 }}>
              <defs>
                {Object.entries(MODE_COLORS).map(([k, color]) => (
                  <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={color} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <XAxis dataKey="month" tick={{ fontSize: 8, fill: '#475569' }}
                tickFormatter={m => m.slice(2, 7)} interval={11} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 8, fill: '#475569' }} tickLine={false} axisLine={false} />
              <Tooltip content={<TimelineTooltip />} />
              {EXPANSION_LINES.map(e => (
                <ReferenceLine key={e.month} x={e.month} stroke="rgba(255,255,255,0.08)"
                  label={{ value: e.label, fill: '#334155', fontSize: 7, position: 'top', angle: -45, offset: 6 }} />
              ))}
              <Area type="monotone" dataKey="pve" stackId="1" stroke={MODE_COLORS.pve}
                strokeWidth={0} fill={`url(#grad-pve)`} />
              <Area type="monotone" dataKey="pvp" stackId="1" stroke={MODE_COLORS.pvp}
                strokeWidth={0} fill={`url(#grad-pvp)`} />
              <Area type="monotone" dataKey="gambit" stackId="1" stroke={MODE_COLORS.gambit}
                strokeWidth={0} fill={`url(#grad-gambit)`} />
            </AreaChart>
          </ResponsiveContainer>
          {/* Era colour band */}
          <div className="flex mt-1 h-0.5 overflow-hidden">
            {Object.entries(ERA_COLORS).map(([era, color]) => (
              <div key={era} className="flex-1" style={{ background: color, opacity: 0.5 }} title={era} />
            ))}
          </div>
        </div>
      </div>

      {/* ── Mode Donut + Leaderboard ────────────────────────────────────────── */}
      <div className="grid sm:grid-cols-[220px_1fr] gap-6">

        {/* Donut */}
        <div>
          <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
            Mode Breakdown · Click to Filter
          </p>
          <div className="flex flex-col items-center gap-0">
            <PieChart width={180} height={180}>
              <Pie data={pieData} dataKey="hoursPlayed" cx={88} cy={88}
                innerRadius={50} outerRadius={76} strokeWidth={0}
                onClick={(_: unknown, idx: number) => {
                  const m = pieData[idx]?.mode;
                  setActiveMode(prev => prev === m ? null : m);
                }}>
                {pieData.map((entry: ModeBlock & { fill: string }) => (
                  <Cell key={entry.mode}
                    fill={entry.fill}
                    opacity={activeMode && activeMode !== entry.mode ? 0.25 : 1}
                    style={{ cursor: 'pointer' }} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => [`${Number(v).toLocaleString()}h`, 'Hours']}
                contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', fontSize: 11 }} />
            </PieChart>
            <div className="w-full space-y-1.5 mt-1">
              {modes.map(m => (
                <button key={m.mode} onClick={() => setActiveMode(prev => prev === m.mode ? null : m.mode)}
                  className={`w-full flex items-center justify-between px-3 py-1.5 border transition-colors ${
                    activeMode === m.mode ? 'border-white/20 bg-white/4' : 'border-white/5 hover:border-white/12'
                  }`}>
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: MODE_COLORS[m.mode] ?? '#64748b' }} />
                    <span className="font-rajdhani text-[10px] uppercase tracking-widest text-slate-400">{m.label}</span>
                  </span>
                  <span className="font-rajdhani text-[10px] text-slate-600">
                    {m.hoursPlayed.toLocaleString()}h
                    {m.winRate != null && <span className="ml-2 text-slate-700">{m.winRate}% W</span>}
                  </span>
                </button>
              ))}
              {activeMode && (
                <button onClick={() => setActiveMode(null)}
                  className="w-full font-rajdhani text-[9px] uppercase tracking-widest text-slate-700 hover:text-slate-500 py-1">
                  Clear filter
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Activity Leaderboard */}
        <div className="min-w-0">
          <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
            Activity Leaderboard{activeMode ? ` · ${MODE_LABELS[activeMode] ?? activeMode}` : ''}
          </p>
          <div className="border border-white/5 overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/2">
                  <th className="px-3 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 w-8" />
                  <th className="px-2 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600">Activity</th>
                  {(['completions', 'kills', 'fastestMs'] as const).map(k => (
                    <th key={k} onClick={() => toggleSort(k)}
                      className="px-2 py-2 font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 cursor-pointer hover:text-slate-400 text-right whitespace-nowrap select-none">
                      <span className="inline-flex items-center gap-0.5">
                        {k === 'completions' ? 'Clears' : k === 'kills' ? 'Kills' : 'Fastest'}
                        <SortIcon k={k} />
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredActivities.slice(0, 20).map((a) => (
                  <tr key={a.activityHash} className="border-b border-white/4 hover:bg-white/2 transition-colors">
                    <td className="pl-3 py-1.5">
                      {a.imageUrl
                        ? <img src={a.imageUrl} alt="" className="w-8 h-5 object-cover opacity-70" />
                        : <div className="w-8 h-5 bg-white/5" />
                      }
                    </td>
                    <td className="px-2 py-1.5">
                      <p className="font-rajdhani text-xs text-slate-300 leading-none">{a.name}</p>
                      <p className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-wide leading-none mt-0.5">
                        {MODE_LABELS[a.mode] ?? a.mode}
                      </p>
                    </td>
                    <td className="px-2 py-1.5 text-right font-rajdhani text-xs text-white tabular-nums">
                      {a.completions.toLocaleString()}
                    </td>
                    <td className="px-2 py-1.5 text-right font-rajdhani text-xs text-slate-400 tabular-nums">
                      {a.kills.toLocaleString()}
                    </td>
                    <td className="px-2 py-1.5 text-right font-rajdhani text-xs text-slate-500 tabular-nums">
                      {fmtMs(a.fastestMs)}
                    </td>
                  </tr>
                ))}
                {filteredActivities.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center font-inter text-xs text-slate-700">
                      No activities for this mode.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Crucible Career ────────────────────────────────────────────────── */}
      {pvpStats && <CrucibleCareer pvpStats={pvpStats} />}

      {/* ── Ability DNA ─────────────────────────────────────────────────────── */}
      {abilityStats && <AbilityDNA abilityStats={abilityStats} />}

      {/* ── Weapon DNA ─────────────────────────────────────────────────────── */}
      {weaponBuckets.length > 0 && (
        <div>
          <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
            Weapon DNA · Kills by Type
          </p>
          <div className="bg-slate-900/40 border border-white/5 p-3">
            <ResponsiveContainer width="100%" height={weaponBuckets.length * 30}>
              <BarChart data={weaponBuckets} layout="vertical"
                margin={{ top: 0, right: 56, left: 0, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="weaponType" type="category" width={130}
                  tick={{ fontSize: 10, fill: '#64748b', fontFamily: 'Rajdhani, sans-serif' }}
                  tickLine={false} axisLine={false} />
                <Tooltip
                  formatter={(v) => [Number(v).toLocaleString(), 'Kills']}
                  contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', fontSize: 11 }} />
                <Bar dataKey="kills" fill="#d4af37" radius={0} maxBarSize={14}>
                  <LabelList dataKey="pct" position="right"
                    formatter={(v) => `${v}%`}
                    style={{ fontSize: 9, fill: '#64748b', fontFamily: 'Rajdhani, sans-serif' }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

    </div>
  );
}
