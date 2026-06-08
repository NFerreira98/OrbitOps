import { useState } from 'react';
import { ChevronDown, ChevronUp, ArrowLeftRight } from 'lucide-react';

export interface GearPerk {
  name: string;
  description: string;
  icon: string | null;
}

export interface GearItem {
  instanceId: string;
  itemHash: number;
  bucketHash: number;
  power: number;
  name: string;
  icon: string | null;
  itemTypeDisplayName: string | null;
  slot: string;
  lore: {
    title: string | null;
    subtitle: string | null;
    description: string | null;
  } | null;
  perks?: GearPerk[];
}

interface GearCardProps {
  item: GearItem;
  onSwapClick?: (item: GearItem) => void;
}

export function GearCard({ item, onSwapClick }: GearCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-destiny-border bg-destiny-panel backdrop-blur-sm clip-chamfer overflow-hidden">
      <div className="flex items-center gap-3 p-3">
        {item.icon ? (
          <img
            src={`https://www.bungie.net${item.icon}`}
            alt={item.name ?? ''}
            className="w-12 h-12 shrink-0"
          />
        ) : (
          <div className="w-12 h-12 shrink-0 bg-slate-800" />
        )}

        <div className="flex-1 min-w-0">
          <p className="font-rajdhani font-bold text-white tracking-wide truncate">
            {item.name ?? '—'}
          </p>
          <div className="flex items-center gap-2">
            <p className="text-xs text-slate-500 uppercase tracking-widest">
              {item.itemTypeDisplayName ?? item.slot}
            </p>
            {item.power > 0 && (
              <span className="text-xs text-destiny-accent/60 font-rajdhani">✦ {item.power}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {onSwapClick && (
            <button
              onClick={() => onSwapClick(item)}
              className="p-1.5 text-slate-600 hover:text-destiny-accent transition-colors"
              title="Swap item"
            >
              <ArrowLeftRight size={14} />
            </button>
          )}

          {item.lore ? (
            <button
              onClick={() => setOpen((o) => !o)}
              className="p-1 text-slate-500 hover:text-destiny-accent transition-colors"
              title={open ? 'Hide lore' : 'Read lore'}
            >
              {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          ) : (
            <span className="text-xs text-slate-700 tracking-widest uppercase px-1">no lore</span>
          )}
        </div>
      </div>

      {item.perks && item.perks.length > 0 && (
        <div className="px-3 pb-2 pt-0 flex flex-wrap gap-1.5">
          {item.perks.map((perk) => (
            <span
              key={perk.name}
              title={perk.description}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-white/4 border border-white/[0.07] font-rajdhani text-[10px] text-slate-400 tracking-wide leading-none cursor-default hover:border-destiny-accent/30 hover:text-slate-200 transition-colors"
            >
              {perk.icon && (
                <img src={perk.icon} alt="" className="w-3 h-3 opacity-60" />
              )}
              {perk.name}
            </span>
          ))}
        </div>
      )}

      {open && item.lore && (
        <div className="px-4 pb-4 border-t border-destiny-border">
          <div className="mt-3">
            {item.lore.title && (
              <p className="font-cinzel text-sm text-destiny-accent mb-1">{item.lore.title}</p>
            )}
            {item.lore.subtitle && (
              <p className="font-inter text-xs text-slate-400 italic mb-3 border-l border-destiny-accent pl-3">
                {item.lore.subtitle}
              </p>
            )}
            {item.lore.description && (
              <p className="font-inter text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                {item.lore.description}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
