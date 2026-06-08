import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, ArrowRight, PlayCircle } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { PathfinderEntry } from '../types/pathfinder';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CATEGORY_LABEL: Record<string, string> = {
  'raid': 'Raid',
  'dungeon': 'Dungeon',
  'exotic-mission': 'Exotic Mission',
};

const INTEREST_MODES = [
  { id: 'exotic-hunter', label: 'Exotic Hunter' },
  { id: 'new-player',    label: 'Just Starting' },
  { id: 'returning',     label: "I've Been Away" },
  { id: 'raid-curious',  label: 'Ready to Raid' },
  { id: 'solo',          label: 'Solo Player' },
] as const;

type InterestMode = typeof INTEREST_MODES[number]['id'] | null;

function DifficultyDots({ level }: { level: number }) {
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <span
          key={i}
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            i <= level ? 'bg-destiny-accent' : 'bg-white/15',
          )}
        />
      ))}
    </span>
  );
}

function ActivityCard({
  entry,
  onOpenAdvisor,
}: {
  entry: PathfinderEntry;
  onOpenAdvisor?: (activityId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasUnowned = entry.rewards.some(r => !r.acquired);

  return (
    <div
      className={cn(
        'border transition-colors',
        hasUnowned ? 'border-amber-700/30' : 'border-white/8',
      )}
    >
      {/* Card image + header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full text-left"
      >
        <div className="relative h-32 overflow-hidden">
          {entry.imageUrl ? (
            <img
              src={entry.imageUrl}
              alt={entry.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-slate-900" />
          )}
          {/* Gradient overlay */}
          <div className="absolute inset-0 bg-linear-to-t from-black/90 via-black/40 to-black/10" />

          {/* Top badges */}
          <div className="absolute top-2 left-3 flex items-center gap-2">
            <span className="font-rajdhani text-[9px] uppercase tracking-widest bg-black/60 border border-white/15 text-slate-400 px-2 py-0.5">
              {CATEGORY_LABEL[entry.category]}
            </span>
            <DifficultyDots level={entry.difficulty} />
          </div>

          {/* Expand indicator */}
          <div className="absolute top-2 right-3 text-slate-500">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>

          {/* Activity name */}
          <div className="absolute bottom-0 left-0 right-0 px-3 pb-2.5">
            <h3 className="font-cinzel text-sm text-white">{entry.name}</h3>
          </div>
        </div>
      </button>

      {/* Reward strip */}
      <div className="px-3 py-2.5 border-t border-white/6 flex flex-wrap gap-3">
        {entry.rewards.map(reward => (
          <div key={reward.name} className="flex items-center gap-1.5">
            {reward.iconUrl && (
              <img
                src={reward.iconUrl}
                alt={reward.name}
                className={cn(
                  'w-6 h-6 border',
                  reward.acquired ? 'border-white/10 opacity-40' : 'border-amber-600/50',
                )}
              />
            )}
            <div>
              <p className={cn(
                'font-rajdhani text-xs font-semibold leading-none',
                reward.acquired ? 'text-slate-600' : 'text-amber-400',
              )}>
                {reward.name}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <p className={cn(
                  'font-rajdhani text-[9px] uppercase tracking-widest leading-none',
                  reward.acquired ? 'text-slate-700' : 'text-amber-600/70',
                )}>
                  {reward.acquired ? '✓ Owned' : 'Not in your collection'}
                </p>
                {!reward.acquired && (
                  <a
                    href={reward.clipUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="flex items-center gap-0.5 font-rajdhani text-[9px] uppercase tracking-widest text-amber-500/50 hover:text-amber-400 transition-colors"
                  >
                    <PlayCircle size={9} />
                    Watch
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-white/6 bg-white/1">
          <p className="font-inter text-xs text-slate-400 leading-relaxed mt-2.5 mb-3">
            {entry.description}
          </p>
          {onOpenAdvisor && entry.category !== 'exotic-mission' && (
            <button
              onClick={() => onOpenAdvisor(entry.id)}
              className="flex items-center gap-1.5 font-rajdhani text-[10px] uppercase tracking-widest text-destiny-accent/70 hover:text-destiny-accent transition-colors border border-destiny-accent/20 hover:border-destiny-accent/40 px-3 py-1.5"
            >
              Open in Raid Advisor
              <ArrowRight size={10} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="border border-white/6 animate-pulse">
      <div className="h-32 bg-white/4" />
      <div className="px-3 py-2.5 border-t border-white/6 flex gap-3">
        <div className="w-6 h-6 bg-white/6 rounded" />
        <div className="space-y-1.5 flex-1">
          <div className="h-2.5 bg-white/6 rounded w-24" />
          <div className="h-2 bg-white/4 rounded w-16" />
        </div>
      </div>
    </div>
  );
}

interface PathfinderProps {
  membershipType: number;
  membershipId: string;
  accessToken: string;
  onOpenAdvisor?: (activityId: string) => void;
}

export function Pathfinder({ membershipType, membershipId, accessToken, onOpenAdvisor }: PathfinderProps) {
  const [entries, setEntries] = useState<PathfinderEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<InterestMode>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(
      `/api/pathfinder/guide?membership_type=${membershipType}&membership_id=${membershipId}`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    )
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error((body as { detail?: string }).detail ?? `Error ${r.status}`);
        }
        return r.json() as Promise<PathfinderEntry[]>;
      })
      .then(setEntries)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load guide'))
      .finally(() => setLoading(false));
  }, [membershipType, membershipId, accessToken]);

  const visible = (() => {
    if (!mode) return entries;
    let filtered = entries.filter(e => e.tags.includes(mode));
    if (mode === 'raid-curious') filtered = filtered.sort((a, b) => a.difficulty - b.difficulty);
    if (mode === 'exotic-hunter') filtered = filtered.sort((a, b) => {
      const aOwned = a.rewards.every(r => r.acquired) ? 1 : 0;
      const bOwned = b.rewards.every(r => r.acquired) ? 1 : 0;
      return aOwned - bOwned;
    });
    return filtered;
  })();

  const uncollectedCount = entries.filter(e => e.rewards.some(r => !r.acquired)).length;

  return (
    <div className="space-y-6 max-w-2xl">

      {/* Header */}
      <div>
        <h2 className="font-cinzel text-xl text-destiny-accent mb-1">Guardian Guide</h2>
        <p className="font-inter text-sm text-slate-500 leading-relaxed">
          Activities worth doing — with rewards you haven't collected yet highlighted.
          {!loading && uncollectedCount > 0 && (
            <span className="text-amber-500/80"> {uncollectedCount} exotic{uncollectedCount !== 1 ? 's' : ''} still waiting for you.</span>
          )}
        </p>
      </div>

      {/* Interest chips */}
      <div className="flex flex-wrap gap-2">
        {INTEREST_MODES.map(m => (
          <button
            key={m.id}
            onClick={() => setMode(mode === m.id ? null : m.id)}
            className={cn(
              'font-rajdhani text-[10px] uppercase tracking-widest px-3 py-1.5 border transition-colors',
              mode === m.id
                ? 'border-destiny-accent/60 text-destiny-accent bg-destiny-accent/10'
                : 'border-white/10 text-slate-500 hover:border-white/25 hover:text-slate-300',
            )}
          >
            {m.label}
          </button>
        ))}
        {mode && (
          <button
            onClick={() => setMode(null)}
            className="font-rajdhani text-[10px] uppercase tracking-widest px-3 py-1.5 text-slate-700 hover:text-slate-500 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Content */}
      {loading && (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && (
        <p className="font-rajdhani text-sm text-red-400/70 tracking-wide">{error}</p>
      )}

      {!loading && !error && visible.length === 0 && (
        <p className="font-inter text-sm text-slate-600 py-12 text-center">
          No activities match this filter.
        </p>
      )}

      {!loading && !error && visible.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {visible.map(entry => (
            <ActivityCard
              key={entry.id}
              entry={entry}
              onOpenAdvisor={onOpenAdvisor}
            />
          ))}
        </div>
      )}
    </div>
  );
}
