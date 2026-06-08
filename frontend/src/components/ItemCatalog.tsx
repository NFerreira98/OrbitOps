import { useEffect, useState } from 'react';
import { Loader2, Play, Search, X } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface CatalogItem {
  hash: number;
  name: string;
  icon: string | null;
  flavorText: string | null;
  tierType: number;
  itemType: number;
  itemSubType: number;
  classType: number;
  collectibleHash: number | null;
  sourceString: string | null;
}

interface CatalogResponse {
  items: CatalogItem[];
  total: number;
}

const WEAPON_SUBTYPES: Record<number, string> = {
  6: 'Auto Rifle',
  9: 'Hand Cannon',
  10: 'Rocket Launcher',
  11: 'Fusion Rifle',
  12: 'Sniper Rifle',
  13: 'Pulse Rifle',
  14: 'Scout Rifle',
  17: 'Submachine Gun',
  18: 'Sidearm',
  23: 'Grenade Launcher',
  24: 'Trace Rifle',
  25: 'Machine Gun',
  54: 'Bow',
  33: 'Sword',
  56: 'Linear Fusion Rifle',
};

const ARMOR_SUBTYPES: Record<number, string> = {
  26: 'Helmet',
  27: 'Gauntlets',
  28: 'Chest',
  29: 'Legs',
  30: 'Class Item',
};

const CLASS_NAMES: Record<number, string> = {
  0: 'Titan',
  1: 'Hunter',
  2: 'Warlock',
  3: 'All',
};

const DISPLAY_LIMIT = 200;

export function ItemCatalog() {
  const [tier, setTier] = useState<6 | 5>(6);
  const [typeFilter, setTypeFilter] = useState<'all' | 'weapon' | 'armor'>('all');
  const [subtypeFilter, setSubtypeFilter] = useState<number | null>(null);
  const [classFilter, setClassFilter] = useState<number | null>(null);
  const [search, setSearch] = useState('');

  // Cache fetched data per tier so switching back is instant
  const [cache, setCache] = useState<Partial<Record<number, CatalogItem[]>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cache[tier]) return;
    const controller = new AbortController();

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/catalog?tier=${tier}`, {
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`Catalog fetch failed: ${res.status}`);
        const data: CatalogResponse = await res.json();
        setCache((prev) => ({ ...prev, [tier]: data.items }));
      } catch (err: unknown) {
        if ((err as Error).name !== 'AbortError') {
          setError((err as Error).message ?? 'Failed to load catalog.');
        }
      } finally {
        setLoading(false);
      }
    };

    load();
    return () => controller.abort();
  }, [tier, cache]);

  // Reset sub-filters when tier or type changes
  useEffect(() => {
    setSubtypeFilter(null);
    setClassFilter(null);
  }, [tier, typeFilter]);

  const allItems = cache[tier] ?? [];

  const filtered = allItems.filter((item) => {
    if (typeFilter === 'weapon' && item.itemType !== 3) return false;
    if (typeFilter === 'armor' && item.itemType !== 2) return false;
    if (subtypeFilter !== null && item.itemSubType !== subtypeFilter) return false;
    if (classFilter !== null && item.classType !== classFilter && item.classType !== 3)
      return false;
    if (search) {
      const q = search.toLowerCase();
      if (!item.name.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const displayed = filtered.slice(0, DISPLAY_LIMIT);
  const hasMore = filtered.length > DISPLAY_LIMIT;

  // Build weapon subtype options from the currently visible items (filtered to weapons only)
  const weaponItems = allItems.filter((i) => i.itemType === 3);
  const usedSubtypes = [...new Set(weaponItems.map((i) => i.itemSubType))].filter(
    (st) => WEAPON_SUBTYPES[st]
  );
  usedSubtypes.sort((a, b) => (WEAPON_SUBTYPES[a] ?? '').localeCompare(WEAPON_SUBTYPES[b] ?? ''));

  return (
    <div className="space-y-6">
      {/* Tier toggle */}
      <div className="flex items-center gap-2">
        <div className="flex border border-destiny-border overflow-hidden">
          {([6, 5] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTier(t)}
              className={cn(
                'px-5 py-2 font-rajdhani text-sm uppercase tracking-widest transition-colors',
                tier === t
                  ? t === 6
                    ? 'bg-destiny-accent/20 text-destiny-accent'
                    : 'bg-purple-900/30 text-purple-300'
                  : 'bg-destiny-panel text-slate-500 hover:text-slate-300'
              )}
            >
              {t === 6 ? 'Exotic' : 'Legendary'}
            </button>
          ))}
        </div>
        {!loading && allItems.length > 0 && (
          <span className="font-rajdhani text-xs text-slate-600 uppercase tracking-widest">
            {allItems.length} items
          </span>
        )}
      </div>

      {/* Type filter */}
      <div className="flex flex-wrap gap-2">
        {(['all', 'weapon', 'armor'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={cn(
              'px-4 py-1.5 font-rajdhani text-xs uppercase tracking-widest border transition-colors',
              typeFilter === t
                ? 'border-destiny-accent/50 text-destiny-accent bg-destiny-accent/10'
                : 'border-destiny-border text-slate-500 hover:text-slate-300 hover:border-slate-600'
            )}
          >
            {t === 'all' ? 'All Items' : t === 'weapon' ? 'Weapons' : 'Armor'}
          </button>
        ))}

        {/* Weapon subtype pills */}
        {typeFilter === 'weapon' && usedSubtypes.map((st) => (
          <button
            key={st}
            onClick={() => setSubtypeFilter(subtypeFilter === st ? null : st)}
            className={cn(
              'px-3 py-1.5 font-rajdhani text-xs uppercase tracking-widest border transition-colors',
              subtypeFilter === st
                ? 'border-slate-400/50 text-white bg-slate-700/50'
                : 'border-destiny-border text-slate-600 hover:text-slate-400 hover:border-slate-600'
            )}
          >
            {WEAPON_SUBTYPES[st]}
          </button>
        ))}

        {/* Armor class pills */}
        {typeFilter === 'armor' && ([0, 1, 2] as const).map((cls) => (
          <button
            key={cls}
            onClick={() => setClassFilter(classFilter === cls ? null : cls)}
            className={cn(
              'px-3 py-1.5 font-rajdhani text-xs uppercase tracking-widest border transition-colors',
              classFilter === cls
                ? 'border-slate-400/50 text-white bg-slate-700/50'
                : 'border-destiny-border text-slate-600 hover:text-slate-400 hover:border-slate-600'
            )}
          >
            {CLASS_NAMES[cls]}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name…"
          className="w-full bg-destiny-panel border border-destiny-border pl-9 pr-8 py-2 text-sm font-inter text-slate-200 placeholder-slate-600 focus:outline-none focus:border-slate-500 transition-colors"
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400"
          >
            <X size={12} />
          </button>
        )}
      </div>

      {/* State: loading */}
      {loading && (
        <div className="flex items-center gap-3 py-12 justify-center text-slate-500">
          <Loader2 size={18} className="animate-spin" />
          <span className="font-rajdhani uppercase tracking-widest text-sm">
            Loading {tier === 6 ? 'exotics' : 'legendaries'}…
          </span>
        </div>
      )}

      {/* State: error */}
      {error && (
        <p className="text-red-400 text-sm font-rajdhani py-8 text-center">{error}</p>
      )}

      {/* Results count */}
      {!loading && !error && allItems.length > 0 && (
        <p className="font-rajdhani text-xs text-slate-600 uppercase tracking-widest">
          Showing {displayed.length} of {filtered.length} results
          {hasMore && ' — refine your filters to see more'}
        </p>
      )}

      {/* Item grid */}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
          {displayed.map((item) => (
            <ItemCard key={item.hash} item={item} tier={tier} />
          ))}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && allItems.length > 0 && (
        <div className="py-12 text-center">
          <p className="font-rajdhani text-slate-500 uppercase tracking-widest text-sm">
            No items match your filters
          </p>
        </div>
      )}
    </div>
  );
}

function ItemCard({ item, tier }: { item: CatalogItem; tier: number }) {
  const isExotic = tier === 6;
  const isWeapon = item.itemType === 3;
  const subtypeName = isWeapon
    ? WEAPON_SUBTYPES[item.itemSubType]
    : ARMOR_SUBTYPES[item.itemSubType];
  const className = item.classType !== 3 ? CLASS_NAMES[item.classType] : null;

  return (
    <div
      className={cn(
        'flex gap-3 p-3 border bg-destiny-panel/60 transition-colors',
        isExotic
          ? 'border-destiny-accent/20 hover:border-destiny-accent/40'
          : 'border-destiny-border hover:border-slate-600'
      )}
    >
      {/* Icon */}
      {item.icon ? (
        <img
          src={item.icon}
          alt={item.name}
          className="w-12 h-12 shrink-0 object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-12 h-12 shrink-0 bg-slate-800/60" />
      )}

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'font-rajdhani font-semibold text-sm leading-tight truncate',
            isExotic ? 'text-destiny-accent' : 'text-purple-300'
          )}
        >
          {item.name}
        </p>

        {/* Type badge row */}
        <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
          {subtypeName && (
            <span className="font-rajdhani text-[10px] uppercase tracking-widest text-slate-500">
              {subtypeName}
            </span>
          )}
          {className && subtypeName && (
            <span className="text-slate-700 text-[10px]">·</span>
          )}
          {className && (
            <span className="font-rajdhani text-[10px] uppercase tracking-widest text-slate-600">
              {className}
            </span>
          )}
        </div>

        {/* Source string */}
        {item.sourceString ? (
          <p className="font-inter text-[11px] text-slate-400 mt-1 leading-relaxed line-clamp-2">
            {item.sourceString.replace(/^Source:\s*/i, '')}
          </p>
        ) : (
          <p className="font-inter text-[11px] text-slate-700 mt-1 italic">
            Source unknown
          </p>
        )}

        {/* Showcase link — exotics only */}
        {isExotic && (
          <a
            href={`https://www.youtube.com/results?search_query=${encodeURIComponent(item.name + ' destiny 2 exotic')}&sp=EgIQAg%3D%3D`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-2 font-rajdhani text-[10px] uppercase tracking-widest text-red-500/60 hover:text-red-400 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <Play size={9} className="fill-current" />
            Watch showcase
          </a>
        )}
      </div>
    </div>
  );
}
