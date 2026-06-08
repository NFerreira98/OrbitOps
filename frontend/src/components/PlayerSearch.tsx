import { useState } from 'react';
import { Search, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

interface SearchResult {
  membershipType: number;
  membershipId: string;
  displayName: string;
  bungieGlobalDisplayName?: string;
  bungieGlobalDisplayNameCode?: number;
  iconPath?: string;
}

interface PublicGearItem {
  itemHash: number;
  slot: string;
  name: string | null;
  icon: string | null;
  itemTypeDisplayName: string | null;
}

interface PublicCharacter {
  characterId: string;
  className: string;
  light: number;
  emblemPath: string | null;
  gear: PublicGearItem[];
}

const PLATFORM_LABELS: Record<number, string> = {
  1: 'Xbox', 2: 'PSN', 3: 'Steam', 5: 'Stadia', 6: 'Epic',
};

const WEAPON_SLOTS = ['Kinetic', 'Energy', 'Power'];

function CharacterLoadout({ char }: { char: PublicCharacter }) {
  const [open, setOpen] = useState(false);
  const weapons = char.gear.filter(g => WEAPON_SLOTS.includes(g.slot));
  const armor   = char.gear.filter(g => !WEAPON_SLOTS.includes(g.slot));

  return (
    <div className="border border-white/5">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/2 transition-colors"
      >
        <div className="flex items-center gap-3">
          {char.emblemPath && (
            <img src={`https://www.bungie.net${char.emblemPath}`} alt="" className="w-8 h-8 object-cover opacity-70" />
          )}
          <div className="text-left">
            <p className="font-rajdhani font-semibold text-white text-sm tracking-wide">{char.className}</p>
            <p className="font-rajdhani text-[10px] text-destiny-accent/70 tracking-widest">✦ {char.light}</p>
          </div>
        </div>
        {open ? <ChevronUp size={14} className="text-slate-600" /> : <ChevronDown size={14} className="text-slate-600" />}
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-white/5 pt-3 grid sm:grid-cols-2 gap-4">
          <div>
            <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-2">Weapons</p>
            <div className="space-y-1.5">
              {weapons.map(item => (
                <div key={item.itemHash} className="flex items-center gap-2">
                  {item.icon
                    ? <img src={`https://www.bungie.net${item.icon}`} alt="" className="w-8 h-8 object-cover opacity-70" />
                    : <div className="w-8 h-8 bg-white/5" />
                  }
                  <div>
                    <p className="font-rajdhani text-xs text-slate-300 leading-none">{item.name ?? '—'}</p>
                    <p className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-wide">{item.itemTypeDisplayName ?? item.slot}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-2">Armor</p>
            <div className="space-y-1.5">
              {armor.map(item => (
                <div key={item.itemHash} className="flex items-center gap-2">
                  {item.icon
                    ? <img src={`https://www.bungie.net${item.icon}`} alt="" className="w-8 h-8 object-cover opacity-70" />
                    : <div className="w-8 h-8 bg-white/5" />
                  }
                  <div>
                    <p className="font-rajdhani text-xs text-slate-300 leading-none">{item.name ?? '—'}</p>
                    <p className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-wide">{item.slot}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function PlayerSearch() {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [selectedPlayer, setSelectedPlayer] = useState<SearchResult | null>(null);
  const [characters, setCharacters] = useState<PublicCharacter[] | null>(null);

  const runSearch = async () => {
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setSearchError(null);
    setResults(null);
    setSelectedPlayer(null);
    setCharacters(null);
    try {
      const res = await fetch(`/api/player/search?name=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const body = await res.json();
      setResults(body.results ?? []);
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const viewProfile = async (player: SearchResult) => {
    setSelectedPlayer(player);
    setCharacters(null);
    setProfileLoading(true);
    setProfileError(null);
    try {
      const res = await fetch(`/api/player/${player.membershipType}/${player.membershipId}/profile`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const body = await res.json();
      setCharacters(body.characters ?? []);
    } catch (e) {
      setProfileError(e instanceof Error ? e.message : 'Failed to load profile');
    } finally {
      setProfileLoading(false);
    }
  };

  const displayName = (r: SearchResult) =>
    r.bungieGlobalDisplayName
      ? `${r.bungieGlobalDisplayName}#${String(r.bungieGlobalDisplayNameCode ?? '').padStart(4, '0')}`
      : r.displayName;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="font-cinzel text-xl text-destiny-accent mb-1">Guardian Lookup</h2>
        <p className="font-inter text-xs text-slate-600">
          Search by Bungie name (Guardian#1234) or name prefix.
        </p>
      </div>

      {/* Search input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && runSearch()}
          placeholder="Guardian#1234"
          className="flex-1 bg-destiny-panel border border-destiny-border text-slate-200 placeholder-slate-600 font-rajdhani px-4 py-2.5 text-sm focus:outline-none focus:border-destiny-accent/40 transition-colors"
        />
        <button
          onClick={runSearch}
          disabled={searching || !query.trim()}
          className="px-4 py-2.5 border border-destiny-border bg-destiny-panel text-slate-400 hover:text-destiny-accent hover:border-destiny-accent/40 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
        </button>
      </div>

      {searchError && <p className="font-rajdhani text-sm text-red-400/70">{searchError}</p>}

      {/* Search results */}
      {results !== null && results.length === 0 && (
        <p className="font-rajdhani text-sm text-slate-600 tracking-widest uppercase">No guardians found.</p>
      )}

      {results && results.length > 0 && (
        <div className="border border-white/5 overflow-hidden">
          {results.map((r, i) => (
            <button
              key={`${r.membershipType}-${r.membershipId}`}
              onClick={() => viewProfile(r)}
              className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors hover:bg-white/4 ${
                i > 0 ? 'border-t border-white/5' : ''
              } ${selectedPlayer?.membershipId === r.membershipId ? 'bg-white/4' : ''}`}
            >
              <div className="flex items-center gap-3">
                {r.iconPath && (
                  <img src={`https://www.bungie.net${r.iconPath}`} alt="" className="w-5 h-5 opacity-50" />
                )}
                <span className="font-rajdhani text-sm text-slate-200">{displayName(r)}</span>
                <span className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600">
                  {PLATFORM_LABELS[r.membershipType] ?? `Type ${r.membershipType}`}
                </span>
              </div>
              <span className="font-rajdhani text-[9px] uppercase tracking-widest text-destiny-accent/50">
                View →
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Profile view */}
      {profileLoading && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 size={14} className="animate-spin" />
          <span className="font-rajdhani text-xs uppercase tracking-widest">Loading loadout…</span>
        </div>
      )}
      {profileError && <p className="font-rajdhani text-sm text-red-400/70">{profileError}</p>}
      {characters && characters.length > 0 && selectedPlayer && (
        <div>
          <p className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-600 mb-3">
            {displayName(selectedPlayer)} · Equipped Loadout
          </p>
          <div className="space-y-px">
            {characters.map(c => <CharacterLoadout key={c.characterId} char={c} />)}
          </div>
        </div>
      )}
    </div>
  );
}
