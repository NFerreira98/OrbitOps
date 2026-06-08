import { useState, useEffect } from 'react';
import { X, Loader2, Zap, AlertTriangle, Search } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { GearItem } from './GearCard';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface SlotItem {
  instanceId: string;
  itemHash: number;
  name: string;
  power: number;
  element: string;
  itemType: string;
  iconUrl: string | null;
  isExotic: boolean;
  isMasterworked: boolean;
  perks: string[];
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

interface SwapPanelProps {
  equippedItem: GearItem;
  membershipType: number;
  membershipId: string;
  accessToken: string;
  onClose: () => void;
  onEquipped: () => void;
}

export function SwapPanel({
  equippedItem,
  membershipType,
  membershipId,
  accessToken,
  onClose,
  onEquipped,
}: SwapPanelProps) {
  const [items, setItems] = useState<SlotItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [equipStates, setEquipStates] = useState<Record<string, 'idle' | 'loading' | 'done' | 'error'>>({});
  const [query, setQuery] = useState('');

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(
      `/api/gear/slot?bucket_hash=${equippedItem.bucketHash}&membership_type=${membershipType}&membership_id=${membershipId}`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    )
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error((body as { detail?: string }).detail ?? `Error ${r.status}`);
        }
        return r.json() as Promise<SlotItem[]>;
      })
      .then(setItems)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load alternatives'))
      .finally(() => setLoading(false));
  }, [equippedItem.bucketHash, membershipType, membershipId, accessToken]);

  const equip = async (item: SlotItem) => {
    setEquipStates(prev => ({ ...prev, [item.instanceId]: 'loading' }));
    try {
      const res = await fetch('/api/vault/equip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({
          instanceId: item.instanceId,
          itemHash: item.itemHash,
          membershipType,
          membershipId,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail ?? 'Equip failed');
      }
      setEquipStates(prev => ({ ...prev, [item.instanceId]: 'done' }));
      onEquipped();
    } catch {
      setEquipStates(prev => ({ ...prev, [item.instanceId]: 'error' }));
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-[420px] z-50 bg-[#0a0e1a] border-l border-white/8 flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/8 shrink-0">
          <div>
            <p className="font-rajdhani text-[9px] uppercase tracking-[0.3em] text-slate-600 mb-0.5">
              Swap Slot
            </p>
            <h3 className="font-cinzel text-sm text-slate-200">{equippedItem.slot}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-600 hover:text-slate-300 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Currently equipped */}
        <div className="px-5 py-3 border-b border-white/6 shrink-0">
          <p className="font-rajdhani text-[8px] uppercase tracking-widest text-slate-700 mb-2">
            Currently Equipped
          </p>
          <div className="flex items-center gap-3">
            {equippedItem.icon ? (
              <img
                src={`https://www.bungie.net${equippedItem.icon}`}
                alt={equippedItem.name}
                className="w-10 h-10 shrink-0 border border-destiny-accent/30"
              />
            ) : (
              <div className="w-10 h-10 shrink-0 bg-slate-800 border border-white/10" />
            )}
            <div className="min-w-0">
              <p className="font-rajdhani font-bold text-destiny-accent/80 text-sm truncate">
                {equippedItem.name}
              </p>
              <p className="font-rajdhani text-[10px] text-slate-600 uppercase tracking-wide">
                {equippedItem.power > 0 ? `✦ ${equippedItem.power}` : equippedItem.itemTypeDisplayName ?? ''}
              </p>
            </div>
          </div>
        </div>

        {/* Search */}
        {!loading && !error && items.length > 0 && (
          <div className="px-5 py-3 border-b border-white/6 shrink-0">
            <div className="relative">
              <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600 pointer-events-none" />
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search by name, type, element…"
                className="w-full bg-white/3 border border-white/8 text-slate-300 font-rajdhani text-xs pl-8 pr-8 py-2 placeholder:text-slate-700 focus:outline-none focus:border-white/20"
                autoFocus
              />
              {query && (
                <button
                  onClick={() => setQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400 transition-colors"
                >
                  <X size={11} />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Alternatives list */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center gap-2 py-16 text-slate-600">
              <Loader2 size={16} className="animate-spin" />
              <span className="font-rajdhani text-xs uppercase tracking-widest">Scanning vault…</span>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 px-5 py-4 text-red-400/70 font-rajdhani text-sm">
              <AlertTriangle size={14} />
              {error}
            </div>
          )}

          {!loading && !error && items.length === 0 && (
            <p className="font-inter text-xs text-slate-700 text-center py-16 px-6">
              No alternatives in your vault or bags for this slot.
            </p>
          )}

          {!loading && !error && items.length > 0 && (() => {
            const q = query.trim().toLowerCase();
            const visibleItems = q
              ? items.filter(i =>
                  i.name.toLowerCase().includes(q) ||
                  i.itemType.toLowerCase().includes(q) ||
                  i.element.toLowerCase().includes(q) ||
                  i.perks.some(p => p.toLowerCase().includes(q))
                )
              : items;
            return (
            <div className="divide-y divide-white/4">
              {visibleItems.length === 0 && (
                <p className="font-inter text-xs text-slate-700 text-center py-10 px-6">
                  No results for "{query}"
                </p>
              )}
              {visibleItems.map(item => {
                const elemStyle = ELEMENT_STYLE[item.element] ?? ELEMENT_STYLE.Kinetic;
                const state = equipStates[item.instanceId] ?? 'idle';

                return (
                  <div key={item.instanceId} className="flex items-start gap-3 px-5 py-3 hover:bg-white/2 transition-colors">
                    {/* Icon */}
                    {item.iconUrl ? (
                      <img
                        src={item.iconUrl}
                        alt={item.name}
                        className={cn(
                          'w-11 h-11 shrink-0 border',
                          item.isExotic ? 'border-amber-600/50' : 'border-white/10',
                        )}
                      />
                    ) : (
                      <div className="w-11 h-11 shrink-0 bg-slate-800 border border-white/10" />
                    )}

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-1.5 flex-wrap">
                        <span className={cn(
                          'font-rajdhani font-bold text-sm truncate',
                          item.isExotic ? 'text-amber-400' : 'text-slate-200',
                        )}>
                          {item.isExotic && <span className="mr-0.5 text-amber-500/70">★</span>}
                          {item.name}
                        </span>
                        {item.isMasterworked && (
                          <span className="font-rajdhani text-[9px] text-amber-500/60">★ MW</span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="font-rajdhani text-[10px] text-slate-500">
                          {item.power > 0 ? `✦ ${item.power}` : '—'}
                        </span>
                        {item.element !== 'Kinetic' && (
                          <span className={cn(
                            'font-rajdhani text-[8px] uppercase tracking-wide border px-1 py-0.5',
                            elemStyle.text, elemStyle.border, elemStyle.bg,
                          )}>
                            {item.element}
                          </span>
                        )}
                        <span className="font-rajdhani text-[9px] text-slate-600 truncate">
                          {item.itemType}
                        </span>
                      </div>

                      {item.perks.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {item.perks.slice(0, 4).map(perk => (
                            <span
                              key={perk}
                              className="font-rajdhani text-[8px] uppercase tracking-wide text-slate-500 bg-white/4 border border-white/8 px-1.5 py-0.5"
                            >
                              {perk}
                            </span>
                          ))}
                          {item.perks.length > 4 && (
                            <span className="font-rajdhani text-[8px] text-slate-700">
                              +{item.perks.length - 4}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Equip button */}
                    <button
                      onClick={() => equip(item)}
                      disabled={state === 'loading' || state === 'done'}
                      className={cn(
                        'shrink-0 flex items-center gap-1 px-2.5 py-1.5 border font-rajdhani text-[9px] uppercase tracking-widest transition-colors mt-0.5',
                        state === 'done'
                          ? 'border-emerald-700/40 text-emerald-500/60 bg-emerald-950/20'
                          : state === 'error'
                            ? 'border-red-700/40 text-red-400/60'
                            : 'border-white/10 text-slate-500 hover:border-destiny-accent/40 hover:text-destiny-accent disabled:opacity-40 disabled:cursor-not-allowed',
                      )}
                    >
                      {state === 'loading'
                        ? <Loader2 size={9} className="animate-spin" />
                        : <Zap size={9} />
                      }
                      {state === 'done' ? 'Equipped' : state === 'error' ? 'Failed' : 'Equip'}
                    </button>
                  </div>
                );
              })}
            </div>
            );
          })()}
        </div>
      </div>
    </>
  );
}
