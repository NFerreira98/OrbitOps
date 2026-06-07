import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export interface GearItem {
  itemHash: number;
  name: string;
  icon: string | null;
  itemTypeDisplayName: string | null;
  slot: string;
  lore: {
    title: string | null;
    subtitle: string | null;
    description: string | null;
  } | null;
}

export function GearCard({ item }: { item: GearItem }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-destiny-border bg-destiny-panel backdrop-blur-sm clip-chamfer overflow-hidden">
      <div className="flex items-center gap-3 p-3">
        {item.icon ? (
          <img
            src={`https://www.bungie.net${item.icon}`}
            alt={item.name ?? ''}
            className="w-12 h-12 flex-shrink-0"
          />
        ) : (
          <div className="w-12 h-12 flex-shrink-0 bg-slate-800" />
        )}

        <div className="flex-1 min-w-0">
          <p className="font-rajdhani font-bold text-white tracking-wide truncate">
            {item.name ?? '—'}
          </p>
          <p className="text-xs text-slate-500 uppercase tracking-widest">
            {item.itemTypeDisplayName ?? item.slot}
          </p>
        </div>

        {item.lore && (
          <button
            onClick={() => setOpen((o) => !o)}
            className="flex-shrink-0 text-slate-500 hover:text-destiny-accent transition-colors p-1"
            title={open ? 'Hide lore' : 'Read lore'}
          >
            {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        )}

        {!item.lore && (
          <span className="text-xs text-slate-700 tracking-widest uppercase flex-shrink-0">
            no lore
          </span>
        )}
      </div>

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
