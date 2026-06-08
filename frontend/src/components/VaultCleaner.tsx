import { useState, useEffect } from 'react';
import { Loader2, Sparkles, Zap, AlertTriangle } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { VaultWeaponGroup, VaultWeaponCopy } from '../types/vault';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const ELEMENT_STYLE: Record<string, { text: string; border: string; bg: string }> = {
  Solar:     { text: 'text-amber-400',   border: 'border-amber-700/40',   bg: 'bg-amber-950/30'   },
  Arc:       { text: 'text-blue-400',    border: 'border-blue-700/40',    bg: 'bg-blue-950/30'    },
  Void:      { text: 'text-purple-400',  border: 'border-purple-700/40',  bg: 'bg-purple-950/30'  },
  Stasis:    { text: 'text-cyan-400',    border: 'border-cyan-700/40',    bg: 'bg-cyan-950/30'    },
  Strand:    { text: 'text-emerald-400', border: 'border-emerald-700/40', bg: 'bg-emerald-950/30' },
  Prismatic: { text: 'text-slate-300',   border: 'border-slate-600/40',   bg: 'bg-slate-800/30'   },
  Kinetic:   { text: 'text-slate-400',   border: 'border-slate-600/30',   bg: 'bg-slate-900/30'   },
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-destiny-accent/50 font-rajdhani text-xs leading-none">//</span>
      <span className="font-cinzel text-[10px] tracking-[0.3em] uppercase text-slate-300">{label}</span>
      <div className="h-px flex-1 bg-white/6" />
    </div>
  );
}

function CopyRow({
  copy,
  index,
  equipState,
  onEquip,
}: {
  copy: VaultWeaponCopy;
  index: number;
  equipState: 'idle' | 'loading' | 'done' | 'error';
  onEquip: () => void;
}) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-white/4 last:border-0">
      {/* Copy number + power */}
      <div className="shrink-0 w-16 text-right">
        <span className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-widest block">
          Copy #{index + 1}
        </span>
        <span className="font-rajdhani text-xs text-slate-300 font-semibold">
          {copy.power > 0 ? `✦ ${copy.power}` : '—'}
        </span>
        {copy.isMasterworked && (
          <span className="font-rajdhani text-[8px] text-amber-500/70 block">★ MW</span>
        )}
      </div>

      {/* Perks */}
      <div className="flex-1 flex flex-wrap gap-1 pt-0.5">
        {copy.perks.length > 0 ? (
          copy.perks.map((perk) => (
            <span
              key={perk}
              className="font-rajdhani text-[9px] uppercase tracking-wide text-slate-400 bg-white/4 border border-white/8 px-1.5 py-0.5"
            >
              {perk}
            </span>
          ))
        ) : (
          <span className="font-inter text-[10px] text-slate-700 italic">No perk data</span>
        )}
      </div>

      {/* Equip button */}
      <button
        onClick={onEquip}
        disabled={equipState === 'loading' || equipState === 'done'}
        className={cn(
          'shrink-0 flex items-center gap-1 px-2.5 py-1 border font-rajdhani text-[9px] uppercase tracking-widest transition-colors',
          equipState === 'done'
            ? 'border-emerald-700/40 text-emerald-500/60 bg-emerald-950/20'
            : equipState === 'error'
              ? 'border-red-700/40 text-red-400/60'
              : 'border-white/10 text-slate-500 hover:border-white/25 hover:text-slate-300 disabled:opacity-40',
        )}
      >
        {equipState === 'loading' ? (
          <Loader2 size={8} className="animate-spin" />
        ) : (
          <Zap size={8} />
        )}
        {equipState === 'done' ? 'Equipped' : equipState === 'error' ? 'Failed' : 'Equip'}
      </button>
    </div>
  );
}

function WeaponGroupCard({
  group,
  evaluation,
  equipStates,
  onEvaluate,
  onEquip,
}: {
  group: VaultWeaponGroup;
  evaluation: { text: string; loading: boolean } | undefined;
  equipStates: Record<string, 'idle' | 'loading' | 'done' | 'error'>;
  onEvaluate: () => void;
  onEquip: (copy: VaultWeaponCopy) => void;
}) {
  const elemStyle = ELEMENT_STYLE[group.element] ?? ELEMENT_STYLE.Kinetic;

  return (
    <div className="border border-white/8 bg-white/[0.02]">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-white/6">
        {group.iconUrl && (
          <img
            src={group.iconUrl}
            alt={group.name}
            className="w-9 h-9 object-cover shrink-0 border border-white/10"
          />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className={cn('font-cinzel text-sm', group.isExotic ? 'text-amber-400' : 'text-slate-200')}>
              {group.isExotic && <span className="mr-1 text-amber-500/80">★</span>}
              {group.name}
            </span>
            <span className={cn(
              'font-rajdhani text-[9px] uppercase tracking-widest border px-1.5 py-0.5',
              elemStyle.text, elemStyle.border, elemStyle.bg,
            )}>
              {group.element}
            </span>
            <span className="font-rajdhani text-[9px] uppercase tracking-wide text-slate-600">
              {group.weaponType}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <span className="font-rajdhani text-xs text-slate-500">
            {group.copies.length} copies
          </span>
          <button
            onClick={onEvaluate}
            disabled={evaluation?.loading}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-destiny-accent/30 text-destiny-accent/70 hover:border-destiny-accent/60 hover:text-destiny-accent transition-colors font-rajdhani text-[10px] uppercase tracking-widest disabled:opacity-40"
          >
            {evaluation?.loading
              ? <Loader2 size={10} className="animate-spin" />
              : <Sparkles size={10} />
            }
            Ask Banshee
          </button>
        </div>
      </div>

      {/* Copy rows */}
      <div className="px-4">
        {group.copies.map((copy, i) => (
          <CopyRow
            key={copy.instanceId}
            copy={copy}
            index={i}
            equipState={equipStates[copy.instanceId] ?? 'idle'}
            onEquip={() => onEquip(copy)}
          />
        ))}
      </div>

      {/* Claude evaluation */}
      {evaluation && !evaluation.loading && evaluation.text && (
        <div className="px-4 py-3 border-t border-destiny-accent/10 bg-destiny-accent/[0.03] space-y-1.5">
          {evaluation.text.split('\n').filter(l => l.trim()).map((line, i) => {
            const isKeep = line.startsWith('Keep:');
            const isShard = line.startsWith('Shard:');
            return (
              <div key={i} className={cn('flex items-start gap-2', (isKeep || isShard) && 'mt-1')}>
                {i === 0 && <Sparkles size={10} className="text-destiny-accent/50 shrink-0 mt-0.5" />}
                {i !== 0 && <span className="w-2.5 shrink-0" />}
                <p className={cn(
                  'font-inter text-xs leading-relaxed',
                  isKeep  ? 'text-emerald-400 font-semibold' :
                  isShard ? 'text-red-400/80 font-semibold'  :
                            'text-slate-300/90',
                )}>
                  {line}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface VaultCleanerProps {
  membershipType: number;
  membershipId: string;
  accessToken: string;
}

export function VaultCleaner({ membershipType, membershipId, accessToken }: VaultCleanerProps) {
  const [groups, setGroups] = useState<VaultWeaponGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [evaluations, setEvaluations] = useState<Record<number, { text: string; loading: boolean }>>({});
  const [equipStates, setEquipStates] = useState<Record<string, 'idle' | 'loading' | 'done' | 'error'>>({});
  const [visibleCount, setVisibleCount] = useState(5);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(
      `/api/vault/weapons?membership_type=${membershipType}&membership_id=${membershipId}`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    )
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error((body as { detail?: string }).detail ?? `Error ${r.status}`);
        }
        return r.json() as Promise<VaultWeaponGroup[]>;
      })
      .then(setGroups)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load vault'))
      .finally(() => setLoading(false));
  }, [membershipType, membershipId, accessToken]);

  const evaluate = async (group: VaultWeaponGroup) => {
    setEvaluations(prev => ({ ...prev, [group.weaponHash]: { text: '', loading: true } }));
    try {
      const res = await fetch('/api/vault/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ group }),
      });
      if (!res.ok) throw new Error(`Evaluate failed: ${res.status}`);
      const data = await res.json() as { recommendation: string };
      setEvaluations(prev => ({ ...prev, [group.weaponHash]: { text: data.recommendation, loading: false } }));
    } catch (e) {
      setEvaluations(prev => ({
        ...prev,
        [group.weaponHash]: { text: 'Evaluation failed — try again.', loading: false },
      }));
    }
  };

  const equip = async (group: VaultWeaponGroup, copy: VaultWeaponCopy) => {
    setEquipStates(prev => ({ ...prev, [copy.instanceId]: 'loading' }));
    try {
      const res = await fetch('/api/vault/equip', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          instanceId: copy.instanceId,
          itemHash: group.weaponHash,
          membershipType,
          membershipId,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail ?? 'Equip failed');
      }
      setEquipStates(prev => ({ ...prev, [copy.instanceId]: 'done' }));
    } catch {
      setEquipStates(prev => ({ ...prev, [copy.instanceId]: 'error' }));
    }
  };

  const totalDuplicateSlots = groups.reduce((sum, g) => sum + g.copies.length - 1, 0);

  return (
    <div className="space-y-8 max-w-2xl">

      {/* Header */}
      <div>
        <h2 className="font-cinzel text-xl text-destiny-accent mb-1">Vault Cleaner</h2>
        <p className="font-inter text-sm text-slate-500 leading-relaxed">
          Weapons you own more than once. Claude explains which roll to keep — you equip it directly from here.
        </p>
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-slate-500 py-16 justify-center">
          <Loader2 className="animate-spin" size={18} />
          <span className="font-rajdhani uppercase tracking-widest text-sm">
            Scanning vault…
          </span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-400/70 font-rajdhani text-sm tracking-wide">
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      {!loading && !error && groups.length === 0 && (
        <p className="font-inter text-sm text-slate-600 py-12 text-center">
          No duplicate weapons found — your vault is clean.
        </p>
      )}

      {!loading && !error && groups.length > 0 && (
        <div className="space-y-6">
          <div>
            <SectionHeader label="Duplicate Groups" />
            <p className="font-rajdhani text-[10px] text-slate-600 uppercase tracking-widest -mt-1 mb-4">
              {groups.length} weapon{groups.length !== 1 ? 's' : ''} with duplicates
              {' · '}{totalDuplicateSlots} redundant slot{totalDuplicateSlots !== 1 ? 's' : ''}
            </p>
            <div className="space-y-3">
              {groups.slice(0, visibleCount).map(group => (
                <WeaponGroupCard
                  key={group.weaponHash}
                  group={group}
                  evaluation={evaluations[group.weaponHash]}
                  equipStates={equipStates}
                  onEvaluate={() => evaluate(group)}
                  onEquip={(copy) => equip(group, copy)}
                />
              ))}
            </div>

            {visibleCount < groups.length && (
              <button
                onClick={() => setVisibleCount(c => c + 5)}
                className="w-full py-2.5 border border-white/8 text-slate-500 hover:border-white/20 hover:text-slate-300 transition-colors font-rajdhani text-xs uppercase tracking-widest"
              >
                Show more · {groups.length - visibleCount} remaining
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
