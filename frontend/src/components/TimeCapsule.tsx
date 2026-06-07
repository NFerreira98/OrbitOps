import { useRef, useState } from 'react';
import html2canvas from 'html2canvas';
import { Download, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { CapsuleData, SeasonEntry, EraActivity, MonthlyPoint } from '../types/capsule';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CLASS_COLORS: Record<string, string> = {
  Titan: 'text-blue-400',
  Hunter: 'text-green-400',
  Warlock: 'text-purple-400',
};

const ERA_ORDER = [
  'Red War',
  'Forsaken',
  'Shadowkeep',
  'Beyond Light',
  'Witch Queen',
  'Lightfall',
  'The Final Shape',
];

const ERA_COLOR: Record<string, string> = {
  'Red War':         '#ef4444',
  'Forsaken':        '#f97316',
  'Shadowkeep':      '#8b5cf6',
  'Beyond Light':    '#3b82f6',
  'Witch Queen':     '#22c55e',
  'Lightfall':       '#ec4899',
  'The Final Shape': '#d4af37',
};

const ERA_ABBR: Record<string, string> = {
  'Red War':         'RW',
  'Forsaken':        'FOR',
  'Shadowkeep':      'SK',
  'Beyond Light':    'BL',
  'Witch Queen':     'WQ',
  'Lightfall':       'LF',
  'The Final Shape': 'TFS',
};

// ── Utilities ─────────────────────────────────────────────────────────────────

function fmt(n: number): string {
  return n.toLocaleString();
}

function fmtDate(iso: string | null | undefined, style: 'short' | 'long' = 'short'): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US',
    style === 'short'
      ? { month: 'short', year: 'numeric' }
      : { month: 'long', day: 'numeric', year: 'numeric' }
  );
}

// ── Small building-block components ───────────────────────────────────────────

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 border-b border-white/5 last:border-0">
      <span className="font-rajdhani text-xs text-slate-500 uppercase tracking-widest">{label}</span>
      <span className="font-rajdhani font-bold text-white text-lg tabular-nums">{value}</span>
    </div>
  );
}

function SeasonDot({ season }: { season: SeasonEntry }) {
  return (
    <div
      title={`S${season.seasonNumber}: ${season.name}`}
      className={cn(
        'w-2.5 h-2.5 rounded-sm',
        season.wasActive
          ? 'bg-destiny-accent/80'
          : 'bg-slate-700/40 border border-white/6'
      )}
    />
  );
}

function EraBlock({ era, seasons }: { era: string; seasons: SeasonEntry[] }) {
  const activeCount = seasons.filter(s => s.wasActive).length;
  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-rajdhani text-[9px] tracking-[0.18em] uppercase text-slate-600 whitespace-nowrap">
        {era}
      </span>
      <div className="flex flex-wrap gap-1">
        {seasons.map(s => <SeasonDot key={s.hash || s.seasonNumber} season={s} />)}
      </div>
      <span className="font-rajdhani text-[9px] text-slate-700 tabular-nums">
        {activeCount}/{seasons.length}
      </span>
    </div>
  );
}

// ── Era bar chart (compact, inside the exportable card) ───────────────────────

function EraBarChart({ eraActivity }: { eraActivity: EraActivity[] }) {
  const BAR_MAX_PX = 52;
  return (
    <div>
      <p className="font-rajdhani text-[10px] tracking-[0.25em] uppercase text-slate-600 mb-3">
        Era Activity
      </p>
      <div className="flex items-end gap-2">
        {eraActivity.map(ea => (
          <div key={ea.era} className="flex flex-col items-center gap-1 flex-1">
            <span
              className="font-rajdhani text-[9px] text-slate-500 tabular-nums"
              title={`${ea.activities.toLocaleString()} activities, ${ea.monthsActive} months`}
            >
              {ea.activities >= 1000
                ? `${(ea.activities / 1000).toFixed(1)}k`
                : ea.activities}
            </span>
            <div
              style={{
                height: `${Math.max(3, Math.round(ea.relativeActivity * BAR_MAX_PX))}px`,
                backgroundColor: ERA_COLOR[ea.era] || '#64748b',
                opacity: 0.65,
                width: '100%',
              }}
            />
            <span
              className="font-rajdhani text-[8px] text-slate-600 uppercase"
              title={ea.era}
            >
              {ERA_ABBR[ea.era] || ea.era.slice(0, 3)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Bookends (first/last timestamps) ──────────────────────────────────────────

function BookendRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="font-rajdhani text-[10px] uppercase tracking-widest text-slate-600">{label}</span>
      <span className="font-rajdhani text-xs text-slate-300 tabular-nums">{value}</span>
    </div>
  );
}

// ── Monthly heatmap (interactive, outside the card) ───────────────────────────

function MonthlyHeatmap({ monthlyData }: { monthlyData: MonthlyPoint[] }) {
  if (!monthlyData.length) return null;

  const maxActs = Math.max(...monthlyData.map(m => m.activities));
  const presentEras = ERA_ORDER.filter(era => monthlyData.some(m => m.era === era));

  return (
    <div className="w-full max-w-2xl">
      <div className="flex items-center gap-3 mb-4">
        <div className="h-px flex-1 bg-white/5" />
        <span className="font-cinzel text-[10px] tracking-[0.3em] uppercase text-slate-600">
          Activity Over Time
        </span>
        <div className="h-px flex-1 bg-white/5" />
      </div>

      <div className="flex flex-wrap gap-0.75">
        {monthlyData.map(mp => {
          const intensity = mp.activities / maxActs;
          const color = ERA_COLOR[mp.era] || '#64748b';
          return (
            <div
              key={mp.period}
              title={`${mp.period} · ${mp.activities.toLocaleString()} activities · ${mp.era}`}
              style={{
                width: 14,
                height: 14,
                backgroundColor: color,
                opacity: 0.12 + intensity * 0.88,
                borderRadius: 2,
              }}
            />
          );
        })}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-4">
        {presentEras.map(era => (
          <div key={era} className="flex items-center gap-1.5">
            <div
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: ERA_COLOR[era], opacity: 0.75 }}
            />
            <span className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-wider">
              {era}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-1.5 ml-2">
          <div className="flex gap-px items-end">
            {[0.15, 0.35, 0.6, 0.85, 1.0].map((o, i) => (
              <div key={i} style={{ width: 8, height: 8, backgroundColor: '#64748b', opacity: o, borderRadius: 1 }} />
            ))}
          </div>
          <span className="font-rajdhani text-[9px] text-slate-700 uppercase tracking-wider">
            activity
          </span>
        </div>
      </div>
    </div>
  );
}

// ── What You Missed accordion ──────────────────────────────────────────────────

function WhatYouMissed({ seasons }: { seasons: SeasonEntry[] }) {
  const [openEra, setOpenEra] = useState<string | null>(null);

  const missedByEra = ERA_ORDER.reduce<Record<string, SeasonEntry[]>>((acc, era) => {
    const missed = seasons.filter(s => s.era === era && !s.wasActive && s.description.length > 30);
    if (missed.length) acc[era] = missed;
    return acc;
  }, {});

  if (!Object.keys(missedByEra).length) return null;

  return (
    <div className="w-full max-w-2xl space-y-3">
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-white/5" />
        <span className="font-cinzel text-[10px] tracking-[0.3em] uppercase text-slate-600">
          What You Missed
        </span>
        <div className="h-px flex-1 bg-white/5" />
      </div>

      <div className="space-y-1">
        {Object.entries(missedByEra).map(([era, missedSeasons]) => (
          <div key={era} className="border border-white/5 bg-white/1.5">
            <button
              onClick={() => setOpenEra(openEra === era ? null : era)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/3 transition-colors"
            >
              <div className="flex items-center gap-3">
                {openEra === era
                  ? <ChevronDown size={12} className="text-slate-600 shrink-0" />
                  : <ChevronRight size={12} className="text-slate-600 shrink-0" />
                }
                <span className="font-rajdhani text-xs uppercase tracking-widest text-slate-400">
                  {era}
                </span>
              </div>
              <span className="font-rajdhani text-xs text-slate-600">
                {missedSeasons.length} season{missedSeasons.length !== 1 ? 's' : ''}
              </span>
            </button>

            {openEra === era && (
              <div className="px-4 pb-4 space-y-5 border-t border-white/5 pt-3">
                {missedSeasons.map(s => (
                  <div key={s.hash || s.seasonNumber} className="space-y-1.5">
                    <p className="font-rajdhani text-xs tracking-widest uppercase text-amber-600/60">
                      {s.name}
                    </p>
                    <p className="font-inter text-sm text-slate-400/80 leading-relaxed">
                      {s.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <p className="font-rajdhani text-[10px] text-slate-700 tracking-wide text-center pt-1">
        — Not every chapter can be lived. Some must only be remembered. —
      </p>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface TimeCapsuleProps {
  data: CapsuleData;
}

export function TimeCapsule({ data }: TimeCapsuleProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(false);

  const handleDownload = async () => {
    if (!cardRef.current) return;
    setExporting(true);
    setExportError(false);
    try {
      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: '#0f172a',
        scale: 2,
        useCORS: true,
        allowTaint: false,
      });
      const link = document.createElement('a');
      link.download = `${data.guardianName}-time-capsule.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch {
      setExportError(true);
    } finally {
      setExporting(false);
    }
  };

  const seasonsByEra = ERA_ORDER.reduce<Record<string, SeasonEntry[]>>((acc, era) => {
    const eraSeasons = data.seasons.filter(s => s.era === era);
    if (eraSeasons.length) acc[era] = eraSeasons;
    return acc;
  }, {});

  const hasTimeline = data.seasons.some(s => s.wasActive);
  const hasMissed = data.seasons.some(s => !s.wasActive && s.description.length > 30) && hasTimeline;
  const hasBookend = !!(
    data.raidBookend.firstCharacterDate ||
    data.raidBookend.firstRaidDate ||
    data.raidBookend.lastRaidDate
  );

  return (
    <div className="flex flex-col items-center gap-6 py-4">

      {/* ── Capturable card ── */}
      <div
        ref={cardRef}
        className="w-full max-w-2xl bg-destiny-dark border border-white/10 p-8 space-y-6"
      >

        {/* Header */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="font-rajdhani text-[10px] tracking-[0.3em] uppercase text-slate-600">
              OrbitOps // Time Capsule
            </span>
            <span className="font-rajdhani text-[10px] tracking-[0.2em] uppercase text-slate-600 border border-slate-700 px-2 py-0.5">
              {data.platform}
            </span>
          </div>

          <h1 className={cn(
            'font-cinzel text-destiny-accent drop-shadow-[0_0_8px_rgba(212,175,55,0.3)]',
            data.guardianName.length > 20 ? 'text-2xl' : 'text-3xl'
          )}>
            {data.guardianName}
          </h1>

          <div className="flex items-center gap-2.5 mt-1.5">
            <span className="font-rajdhani text-xs uppercase tracking-widest text-slate-500">
              {data.archetype}
            </span>
            <span className="text-slate-700 text-xs">·</span>
            <span className="font-rajdhani text-xs text-slate-600 tracking-wider">
              {data.yearsActive} Year{data.yearsActive !== 1 ? 's' : ''} of Service
            </span>
          </div>

          <div className="h-px w-full bg-linear-to-r from-destiny-accent/60 via-destiny-accent/20 to-transparent mt-3" />
        </div>

        {/* Characters */}
        <div className="space-y-3">
          <div className="flex flex-wrap gap-3">
            {data.characters.map((char) => (
              <div
                key={char.characterId}
                className={cn(
                  'relative flex items-center gap-3 px-3 py-2 border overflow-hidden',
                  char.isPrimary
                    ? 'border-destiny-accent/60 bg-destiny-accent/5'
                    : 'border-white/10 bg-white/2'
                )}
                style={char.emblemBackgroundPath ? {
                  backgroundImage: `linear-gradient(to right, rgba(15,23,42,0.92), rgba(15,23,42,0.75)), url(https://www.bungie.net${char.emblemBackgroundPath})`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                } : undefined}
              >
                {char.emblemPath && (
                  <img
                    src={`https://www.bungie.net${char.emblemPath}`}
                    alt=""
                    crossOrigin="anonymous"
                    className="w-8 h-8 shrink-0"
                  />
                )}
                <div>
                  <p className={cn('font-cinzel text-xs font-bold', CLASS_COLORS[char.className] ?? 'text-white')}>
                    {char.className}
                  </p>
                  <p className="font-rajdhani text-xs text-destiny-accent/80 tracking-widest">
                    ✦ {char.light}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {data.titles.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {data.titles.map((title) => (
                <span
                  key={title}
                  className="font-rajdhani text-xs tracking-widest uppercase text-amber-500/70 border border-amber-800/40 px-2 py-0.5"
                >
                  {title}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Rarest Achievement spotlight */}
        {data.prestigeAchievement && (
          <div className="border border-amber-800/30 bg-amber-950/10 px-4 py-3 space-y-1.5">
            <p className="font-rajdhani text-[10px] tracking-[0.25em] uppercase text-amber-700/50">
              Rarest Achievement
            </p>
            <div className="flex items-center gap-2.5">
              <span className="font-cinzel text-sm text-amber-400/90 tracking-wider">
                {data.prestigeAchievement.name}
              </span>
              <div className="flex gap-0.5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      'w-1.5 h-1.5 rounded-full',
                      i < data.prestigeAchievement!.tier ? 'bg-amber-500/75' : 'bg-slate-700'
                    )}
                  />
                ))}
              </div>
            </div>
            <p className="font-inter text-xs text-slate-400/70 leading-relaxed">
              {data.prestigeAchievement.description}
            </p>
          </div>
        )}

        {/* Season Timeline */}
        {hasTimeline && (
          <div>
            <p className="font-rajdhani text-[10px] tracking-[0.25em] uppercase text-slate-600 mb-3">
              Journey
            </p>
            <div className="flex flex-wrap gap-x-5 gap-y-3">
              {ERA_ORDER.map(era => {
                const eraSeasons = seasonsByEra[era];
                if (!eraSeasons?.length) return null;
                return <EraBlock key={era} era={era} seasons={eraSeasons} />;
              })}
            </div>
            <div className="flex items-center gap-3 mt-3">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-sm bg-destiny-accent/80" />
                <span className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-wider">Active</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-sm bg-slate-700/40 border border-white/6" />
                <span className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-wider">Away</span>
              </div>
            </div>
          </div>
        )}

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="font-rajdhani text-[10px] tracking-[0.25em] uppercase text-slate-600 mb-2">
              Field Record
            </p>
            <StatRow label="Hours" value={fmt(Math.round(data.hoursPlayed))} />
            <StatRow label="Kills" value={fmt(data.totalKills)} />
            <StatRow label="Precision" value={`${data.precisionKillPct.toFixed(1)}%`} />
            <StatRow label="Deaths" value={fmt(data.totalDeaths)} />
          </div>

          <div className="space-y-4">
            <div>
              <p className="font-rajdhani text-[10px] tracking-[0.25em] uppercase text-slate-600 mb-2">
                Activities
              </p>
              <StatRow label="Raids" value={fmt(data.raidsCleared)} />
              <StatRow label="Nightfalls" value={fmt(data.nightfallsCleared)} />
              <StatRow label="Strikes" value={fmt(data.strikesCleared)} />
            </div>
            <div>
              <p className="font-rajdhani text-[10px] tracking-[0.25em] uppercase text-slate-600 mb-2">
                Crucible
              </p>
              <StatRow label="Matches" value={fmt(data.pvpMatches)} />
              <StatRow label="Wins" value={fmt(data.pvpWins)} />
              <StatRow label="K/D" value={data.pvpKD.toFixed(2)} />
            </div>
          </div>
        </div>

        {/* Era activity bar chart */}
        {data.eraActivity.length > 0 && (
          <EraBarChart eraActivity={data.eraActivity} />
        )}

        {/* Firsts & Lasts bookends */}
        {hasBookend && (
          <div className="space-y-2">
            <p className="font-rajdhani text-[10px] tracking-[0.25em] uppercase text-slate-600">
              Bookends
            </p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
              {data.raidBookend.firstCharacterDate && (
                <BookendRow label="Guardian Born" value={fmtDate(data.raidBookend.firstCharacterDate)} />
              )}
              <BookendRow label="First Raid" value={fmtDate(data.raidBookend.firstRaidDate)} />
              <BookendRow label="Last Login" value={fmtDate(data.raidBookend.lastLoginDate)} />
              <BookendRow label="Last Raid" value={fmtDate(data.raidBookend.lastRaidDate)} />
            </div>
            {data.raidBookend.raidCount > 0 && data.raidBookend.firstRaidDate && data.raidBookend.lastRaidDate && (
              <p className="font-inter text-[10px] text-slate-600 italic mt-1">
                {fmt(data.raidBookend.raidCount)} raid clears · {fmtDate(data.raidBookend.firstRaidDate)} → {fmtDate(data.raidBookend.lastRaidDate)}
              </p>
            )}
          </div>
        )}

        {/* Ghost narrative */}
        <div className="space-y-3">
          <div className="h-px w-full bg-linear-to-r from-amber-700/50 via-amber-900/20 to-transparent" />
          <p className="font-cinzel text-[10px] tracking-[0.3em] uppercase text-amber-600/50">
            // Ghost
          </p>
          <p className="font-inter text-sm text-amber-50/75 leading-relaxed italic">
            {data.ghostNarrative}
          </p>
        </div>

        {/* What Defined You verdict */}
        {data.verdict && (
          <div className="space-y-2 pt-1">
            <p className="font-cinzel text-[10px] tracking-[0.3em] uppercase text-slate-500/60">
              // What Defined You
            </p>
            <p className="font-rajdhani text-sm text-slate-300/80 leading-relaxed tracking-wide">
              {data.verdict}
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-1">
          <span className="font-rajdhani text-[10px] text-slate-700 tracking-widest uppercase">
            Last seen: {fmtDate(data.dateLastPlayed, 'long')}
          </span>
          <span className="font-rajdhani text-[10px] text-slate-700 tracking-widest uppercase">
            OrbitOps // Bungie.net
          </span>
        </div>
      </div>

      {/* Download button — outside capturable area */}
      <div className="flex flex-col items-center gap-2">
        <button
          onClick={handleDownload}
          disabled={exporting}
          className="flex items-center gap-2 px-6 py-2.5 border border-destiny-accent text-destiny-accent hover:bg-destiny-accent/10 transition-colors clip-chamfer font-rajdhani uppercase tracking-widest text-sm disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {exporting
            ? <><Loader2 size={14} className="animate-spin" /> Rendering…</>
            : <><Download size={14} /> Download Card</>
          }
        </button>
        {exportError && (
          <p className="font-rajdhani text-xs text-red-400/70 tracking-wide">
            Export failed — emblem images may be blocked by CORS. Try again or screenshot manually.
          </p>
        )}
      </div>

      {/* Interactive monthly heatmap — outside capturable area */}
      {data.monthlyData.length > 0 && (
        <MonthlyHeatmap monthlyData={data.monthlyData} />
      )}

      {/* What You Missed accordion — outside capturable area */}
      {hasMissed && <WhatYouMissed seasons={data.seasons} />}
    </div>
  );
}
