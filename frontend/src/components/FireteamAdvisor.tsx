import { useState, useEffect, useRef, type KeyboardEvent } from 'react';
import { Plus, X, Loader2, AlertTriangle, History, ExternalLink } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { MemberProfile, FireteamAnalysis, ActivityInfo, EncounterCard, TeamRole } from '../types/fireteam';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CLASS_COLOR: Record<string, string> = {
  Titan:   'text-blue-400',
  Hunter:  'text-green-400',
  Warlock: 'text-purple-400',
  Unknown: 'text-slate-500',
};

const ELEMENT_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  Solar:     { bg: 'bg-amber-950/30',   text: 'text-amber-400',   border: 'border-amber-700/40' },
  Arc:       { bg: 'bg-blue-950/30',    text: 'text-blue-400',    border: 'border-blue-700/40'  },
  Void:      { bg: 'bg-purple-950/30',  text: 'text-purple-400',  border: 'border-purple-700/40'},
  Stasis:    { bg: 'bg-cyan-950/30',    text: 'text-cyan-400',    border: 'border-cyan-700/40'  },
  Strand:    { bg: 'bg-emerald-950/30', text: 'text-emerald-400', border: 'border-emerald-700/40'},
  Prismatic: { bg: 'bg-slate-800/30',   text: 'text-slate-300',   border: 'border-slate-600/40' },
  Unknown:   { bg: 'bg-slate-900/30',   text: 'text-slate-600',   border: 'border-slate-700/30' },
};

const ALL_ELEMENTS = ['Solar', 'Arc', 'Void', 'Stasis', 'Strand'];

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-destiny-accent/50 font-rajdhani text-xs leading-none">//</span>
      <span className="font-cinzel text-[10px] tracking-[0.3em] uppercase text-slate-300">
        {label}
      </span>
      <div className="h-px flex-1 bg-white/6" />
    </div>
  );
}

function ElementChip({ element, small = false }: { element: string; small?: boolean }) {
  const style = ELEMENT_STYLE[element] ?? ELEMENT_STYLE.Unknown;
  return (
    <span className={cn(
      'font-rajdhani uppercase tracking-wider border',
      small ? 'text-[9px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5',
      style.bg, style.text, style.border,
    )}>
      {element}
    </span>
  );
}

function MemberCard({ member }: { member: MemberProfile }) {
  const classColor = CLASS_COLOR[member.className] ?? CLASS_COLOR.Unknown;
  const hasError = !!member.error;

  return (
    <div className={cn(
      'flex-1 min-w-[160px] max-w-[220px] border p-3 space-y-2',
      hasError
        ? 'border-red-800/40 bg-red-950/10'
        : member.isCurrentUser
          ? 'border-destiny-accent/40 bg-destiny-accent/5'
          : 'border-white/8 bg-white/2',
    )}>
      <div className="flex items-start justify-between gap-1">
        <p className={cn(
          'font-rajdhani text-xs tracking-wide break-all leading-tight',
          hasError ? 'text-red-400/80' : 'text-slate-200',
        )}>
          {member.displayName}
        </p>
        {member.isCurrentUser && (
          <span className="font-rajdhani text-[8px] uppercase tracking-widest text-destiny-accent/60 border border-destiny-accent/30 px-1 shrink-0">
            You
          </span>
        )}
      </div>

      {hasError ? (
        <div className="flex items-center gap-1.5">
          <AlertTriangle size={10} className="text-red-500/70 shrink-0" />
          <p className="font-inter text-[10px] text-red-400/70 leading-tight">{member.error}</p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('font-cinzel text-xs font-bold', classColor)}>
              {member.className}
            </span>
            <ElementChip element={member.subclassElement} small />
          </div>

          <div className="space-y-0.5">
            {member.exoticArmor ? (
              <p className="font-rajdhani text-[10px] text-amber-500/70 truncate">⬡ {member.exoticArmor}</p>
            ) : (
              <p className="font-rajdhani text-[10px] text-slate-700">⬡ No exotic armor</p>
            )}
            {member.exoticWeapon ? (
              <p className="font-rajdhani text-[10px] text-slate-400 truncate">◈ {member.exoticWeapon}</p>
            ) : (
              <p className="font-rajdhani text-[10px] text-slate-700">◈ No exotic weapon</p>
            )}
          </div>

          {member.weaponElements.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {member.weaponElements.map((el, i) => (
                <ElementChip key={i} element={el} small />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function EncounterCardView({ encounter, index }: { encounter: EncounterCard; index: number }) {
  return (
    <div className="w-52 shrink-0 border border-white/8 overflow-hidden bg-slate-950">
      {/* Image with gradient overlay */}
      <div className="relative h-28">
        {encounter.imageUrl ? (
          <img
            src={encounter.imageUrl}
            alt={encounter.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-linear-to-br from-slate-800 to-slate-900" />
        )}
        <div className="absolute inset-0 bg-linear-to-t from-black/90 via-black/30 to-transparent" />

        {/* Encounter number */}
        <div className="absolute top-2 left-2">
          <span className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-400 bg-black/70 px-1.5 py-0.5 border border-white/10">
            #{index + 1}
          </span>
        </div>

        {/* Encounter name overlaid on image bottom */}
        <div className="absolute bottom-0 left-0 right-0 px-2.5 pb-2">
          <p className="font-cinzel text-[11px] text-white leading-tight">{encounter.name}</p>
        </div>
      </div>

      {/* Content below image */}
      <div className="p-2.5 space-y-2 bg-black/30">
        {/* Weapon types */}
        <div className="flex flex-wrap gap-1">
          {encounter.weaponTypes.map(wt => (
            <span
              key={wt}
              className="font-rajdhani text-[8px] uppercase tracking-wide text-slate-500 bg-white/4 border border-white/8 px-1.5 py-0.5"
            >
              {wt}
            </span>
          ))}
        </div>

        {/* Elements */}
        <div className="flex flex-wrap gap-1">
          {encounter.elements.map(el => (
            <ElementChip key={el} element={el} small />
          ))}
        </div>

        {/* Exotics */}
        {encounter.exotics.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {encounter.exotics.map(ex => (
              <span
                key={ex}
                className="font-rajdhani text-[8px] text-amber-500/80 bg-amber-950/20 border border-amber-700/30 px-1.5 py-0.5 truncate max-w-full"
              >
                {ex}
              </span>
            ))}
          </div>
        )}

        {/* Tip */}
        <p className="font-inter text-[10px] text-slate-500 italic leading-relaxed">
          {encounter.tip}
        </p>

        {/* Vault matches */}
        {encounter.vaultMatches.length > 0 && (
          <div className="pt-2 border-t border-white/5">
            <p className="font-rajdhani text-[8px] uppercase tracking-widest text-slate-600 mb-1">
              In your vault
            </p>
            <div className="flex flex-col gap-0.5">
              {encounter.vaultMatches.map(w => (
                <span key={w} className="font-rajdhani text-[10px] text-emerald-400/75 leading-tight">
                  {w}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TeamRoleRow({ team }: { team: TeamRole }) {
  return (
    <div className="flex gap-2 text-[11px]">
      <span className="font-rajdhani font-bold text-destiny-accent/60 shrink-0">{team.label}:</span>
      <span className="font-inter text-slate-400 leading-snug">{team.role}</span>
    </div>
  );
}

function RaidGuide({ activity }: { activity: ActivityInfo }) {
  return (
    <div className="space-y-4">
      <a
        href={activity.videoUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 px-4 py-2 border border-white/15 text-slate-400 hover:border-white/30 hover:text-slate-200 transition-colors font-rajdhani text-xs uppercase tracking-widest"
      >
        <ExternalLink size={12} /> Watch Full Guide on YouTube
      </a>

      <div className="space-y-5">
        {activity.encounters.map((enc, i) => (
          <div key={i} className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-rajdhani text-[9px] text-slate-600 uppercase tracking-widest shrink-0">
                #{i + 1}
              </span>
              <span className="font-cinzel text-xs text-slate-200">{enc.name}</span>
              <div className="h-px flex-1 bg-white/5" />
            </div>

            {enc.teams.length > 0 && (
              <div className="ml-4 space-y-1">
                {enc.teams.map((team, j) => (
                  <TeamRoleRow key={j} team={team} />
                ))}
              </div>
            )}

            {enc.steps.length > 0 && (
              <ul className="ml-4 space-y-1">
                {enc.steps.map((step, j) => (
                  <li key={j} className="flex gap-2 font-inter text-xs text-slate-500 leading-snug">
                    <span className="text-destiny-accent/30 shrink-0 mt-px">→</span>
                    {step}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface FireteamAdvisorProps {
  membershipType: number;
  membershipId: string;
  accessToken: string;
}

export function FireteamAdvisor({
  membershipType,
  membershipId,
  accessToken,
}: FireteamAdvisorProps) {
  const [inputValue, setInputValue] = useState('');
  const [memberInputs, setMemberInputs] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<FireteamAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastActivityLoading, setLastActivityLoading] = useState(false);
  const [lastActivityLabel, setLastActivityLabel] = useState<string | null>(null);

  const [activities, setActivities] = useState<ActivityInfo[]>([]);
  const [selectedActivityId, setSelectedActivityId] = useState('');

  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [highlightedIdx, setHighlightedIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch activity list on mount
  useEffect(() => {
    fetch('/api/fireteam/activities')
      .then(r => r.json())
      .then((data: ActivityInfo[]) => {
        setActivities(data);
        const preselect = sessionStorage.getItem('pathfinder_activity');
        if (preselect) {
          sessionStorage.removeItem('pathfinder_activity');
          setSelectedActivityId(preselect);
        }
      })
      .catch(() => {});
  }, []);

  // Debounced name search
  useEffect(() => {
    const trimmed = inputValue.trim();
    if (trimmed.length < 2) {
      setSuggestions([]);
      setSuggestionsOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/fireteam/search?query=${encodeURIComponent(trimmed)}`);
        if (!res.ok) return;
        const data: { suggestions: string[] } = await res.json();
        setSuggestions(data.suggestions);
        setSuggestionsOpen(data.suggestions.length > 0);
        setHighlightedIdx(-1);
      } catch { /* silently ignore */ }
    }, 300);
    return () => clearTimeout(timer);
  }, [inputValue]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setSuggestionsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const addMember = (name: string) => {
    const trimmed = name.trim();
    if (!trimmed || memberInputs.includes(trimmed) || memberInputs.length >= 5) return;
    setMemberInputs(prev => [...prev, trimmed]);
    setInputValue('');
    setSuggestions([]);
    setSuggestionsOpen(false);
    setHighlightedIdx(-1);
  };

  const removeMember = (name: string) => {
    setMemberInputs(prev => prev.filter(m => m !== name));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (suggestionsOpen && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlightedIdx(i => Math.min(i + 1, suggestions.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlightedIdx(i => Math.max(i - 1, -1));
        return;
      }
      if (e.key === 'Escape') {
        setSuggestionsOpen(false);
        return;
      }
      if (e.key === 'Enter' && highlightedIdx >= 0) {
        e.preventDefault();
        addMember(suggestions[highlightedIdx]);
        return;
      }
    }
    if (e.key === 'Enter') addMember(inputValue);
  };

  const loadLastFireteam = async () => {
    setLastActivityLoading(true);
    setLastActivityLabel(null);
    try {
      const res = await fetch(
        `/api/fireteam/last-activity?membership_type=${membershipType}&membership_id=${membershipId}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      );
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error((detail as { detail?: string }).detail || 'No recent fireteam found');
      }
      const data: { members: string[]; activityMode: string; activityDate: string } = await res.json();
      let added = 0;
      for (const name of data.members) {
        if (!memberInputs.includes(name) && memberInputs.length + added < 5) {
          setMemberInputs(prev => [...prev, name]);
          added++;
        }
      }
      const date = new Date(data.activityDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      setLastActivityLabel(`Loaded ${added} member${added !== 1 ? 's' : ''} from your last ${data.activityMode} · ${date}`);
    } catch (e) {
      setLastActivityLabel(e instanceof Error ? e.message : 'Failed to load last fireteam');
    } finally {
      setLastActivityLoading(false);
    }
  };

  const analyze = async () => {
    setLoading(true);
    setError(null);
    setAnalysis(null);
    try {
      const res = await fetch('/api/fireteam/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          members: memberInputs,
          membership_type: membershipType,
          membership_id: membershipId,
          activity_id: selectedActivityId || null,
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error((detail as { detail?: string }).detail || `Error ${res.status}`);
      }
      const data: FireteamAnalysis = await res.json();
      setAnalysis(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const raids = activities.filter(a => a.type === 'raid');
  const dungeons = activities.filter(a => a.type === 'dungeon');
  const selectedActivity = activities.find(a => a.id === selectedActivityId) ?? null;

  return (
    <div className="space-y-8 max-w-2xl">

      {/* Header */}
      <div>
        <h2 className="font-cinzel text-xl text-destiny-accent mb-1">Fireteam Advisor</h2>
        <p className="font-inter text-sm text-slate-500 leading-relaxed">
          Add your fireteam members by Bungie name to analyze composition — element coverage,
          champion mods, support roles, and redundancies.
        </p>
      </div>

      {/* Input section */}
      <div className="space-y-3">
        <SectionHeader label="Build Your Fireteam" />

        <div className="flex gap-2">
          <div ref={wrapperRef} className="relative flex-1">
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => suggestions.length > 0 && setSuggestionsOpen(true)}
              placeholder="Guardian#1234"
              className="w-full bg-white/3 border border-white/10 text-slate-200 font-rajdhani text-sm px-3 py-2 placeholder:text-slate-700 focus:outline-none focus:border-destiny-accent/40"
            />
            {suggestionsOpen && suggestions.length > 0 && (
              <ul className="absolute z-50 top-full left-0 right-0 mt-0.5 border border-white/10 bg-destiny-dark shadow-xl">
                {suggestions.map((s, i) => (
                  <li
                    key={s}
                    onMouseDown={() => addMember(s)}
                    onMouseEnter={() => setHighlightedIdx(i)}
                    className={cn(
                      'px-3 py-2 font-rajdhani text-sm cursor-pointer transition-colors',
                      i === highlightedIdx
                        ? 'bg-destiny-accent/10 text-destiny-accent'
                        : 'text-slate-300 hover:bg-white/5',
                    )}
                  >
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            onClick={() => addMember(inputValue)}
            disabled={!inputValue.trim() || memberInputs.length >= 5}
            className="flex items-center gap-1.5 px-3 py-2 border border-white/15 text-slate-400 hover:border-white/30 hover:text-slate-200 transition-colors font-rajdhani text-xs uppercase tracking-widest disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Plus size={12} /> Add
          </button>
          <button
            onClick={loadLastFireteam}
            disabled={lastActivityLoading || memberInputs.length >= 5}
            className="flex items-center gap-1.5 px-3 py-2 border border-white/10 text-slate-500 hover:border-white/25 hover:text-slate-300 transition-colors font-rajdhani text-xs uppercase tracking-widest disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {lastActivityLoading
              ? <Loader2 size={12} className="animate-spin" />
              : <History size={12} />
            }
            Last Fireteam
          </button>
        </div>

        {lastActivityLabel && (
          <p className={`font-rajdhani text-[10px] tracking-wide ${
            lastActivityLabel.startsWith('Loaded') ? 'text-slate-500' : 'text-red-400/60'
          }`}>
            {lastActivityLabel}
          </p>
        )}

        <p className="font-rajdhani text-[10px] text-slate-700 tracking-wide">
          You are always included — add up to 5 fireteam members for a full 6-player raid stack.
        </p>

        {/* Member chips */}
        {memberInputs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {memberInputs.map(name => (
              <div key={name} className="flex items-center gap-1.5 border border-white/10 bg-white/3 px-2 py-1">
                <span className="font-rajdhani text-xs text-slate-300">{name}</span>
                <button
                  onClick={() => removeMember(name)}
                  className="text-slate-600 hover:text-slate-300 transition-colors"
                >
                  <X size={10} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Activity selector */}
        <div>
          <label className="font-rajdhani text-[10px] uppercase tracking-widest text-slate-600 mb-1.5 block">
            Activity (optional)
          </label>
          <select
            value={selectedActivityId}
            onChange={e => setSelectedActivityId(e.target.value)}
            className="bg-[#0d1117] border border-white/10 text-slate-300 font-rajdhani text-sm px-3 py-2 w-full focus:outline-none focus:border-white/20 appearance-none cursor-pointer"
          >
            <option value="">— General analysis —</option>
            {raids.length > 0 && (
              <optgroup label="Raids">
                {raids.map(a => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </optgroup>
            )}
            {dungeons.length > 0 && (
              <optgroup label="Dungeons">
                {dungeons.map(a => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </optgroup>
            )}
          </select>
        </div>

        {/* Analyze button */}
        <button
          onClick={analyze}
          disabled={loading}
          className="flex items-center gap-2 px-6 py-2.5 border border-destiny-accent text-destiny-accent hover:bg-destiny-accent/10 transition-colors font-rajdhani uppercase tracking-widest text-sm disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading
            ? <><Loader2 size={14} className="animate-spin" /> Analyzing…</>
            : 'Analyze Composition'
          }
        </button>

        {error && (
          <p className="font-rajdhani text-xs text-red-400/70 tracking-wide">{error}</p>
        )}
      </div>

      {/* Raid Guide — shown as soon as an activity is selected */}
      {selectedActivity && (
        <div>
          <SectionHeader label="Raid Guide" />
          <RaidGuide activity={selectedActivity} />
        </div>
      )}

      {/* Results */}
      {analysis && (
        <div className="space-y-6">

          {/* Member cards */}
          <div>
            <SectionHeader label="Loadout Snapshot" />
            <div className="flex flex-wrap gap-3">
              {analysis.members.map(m => (
                <MemberCard key={m.displayName} member={m} />
              ))}
            </div>
          </div>

          {/* Element coverage */}
          <div>
            <SectionHeader label="Element Coverage" />
            <div className="flex flex-wrap gap-2">
              {ALL_ELEMENTS.map(el => {
                const covered = analysis.elementCoverage.includes(el);
                return (
                  <div key={el} className="flex items-center gap-1.5">
                    <ElementChip element={el} />
                    {!covered && (
                      <span className="font-rajdhani text-[9px] text-red-500/60 uppercase tracking-wider">
                        missing
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
            {analysis.missingElements.length > 0 && (
              <p className="font-inter text-xs text-red-400/60 mt-2 italic">
                Missing elements limit champion mod options — consider swapping a subclass or adding
                weapons of the missing type.
              </p>
            )}
          </div>

          {/* Claude analysis — bullet style */}
          <div>
            <SectionHeader label="Composition Analysis" />
            <div className="border-l-2 border-destiny-accent/20 pl-4 space-y-2">
              {analysis.claudeAnalysis.split('\n').filter(l => l.trim()).map((line, i) => (
                <p key={i} className="font-inter text-sm text-slate-300/90 leading-relaxed">
                  {line}
                </p>
              ))}
            </div>
          </div>

          {/* Encounter breakdown */}
          {analysis.encounterCards.length > 0 && (
            <div>
              <SectionHeader label="Encounter Breakdown" />
              <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
                {analysis.encounterCards.map((enc, i) => (
                  <div key={i} className="snap-start">
                    <EncounterCardView encounter={enc} index={i} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
