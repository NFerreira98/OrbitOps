import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { LogOut, Loader2, Send } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { GearCard, type GearItem } from '../components/GearCard';
import { TimeCapsule } from '../components/TimeCapsule';
import { FireteamAdvisor } from '../components/FireteamAdvisor';
import { VaultCleaner } from '../components/VaultCleaner';
import { SwapPanel } from '../components/SwapPanel';
import { Pathfinder } from '../components/Pathfinder';
import { StatsDashboard } from '../components/StatsDashboard';
import { WeeklyReset } from '../components/WeeklyReset';
import { RecentActivity } from '../components/RecentActivity';
import { PlayerSearch } from '../components/PlayerSearch';
import type { CapsuleData } from '../types/capsule';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CLASS_COLORS: Record<string, string> = {
  Titan: 'text-blue-400',
  Hunter: 'text-green-400',
  Warlock: 'text-purple-400',
};

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: { name: string; hash: string }[];
}

interface Character {
  characterId: string;
  className: string;
  subclassName: string | null;
  light: number;
  emblemPath: string | null;
  emblemBackgroundPath: string | null;
  gear: GearItem[];
}

const WEAPON_SLOTS = ['Kinetic', 'Energy', 'Power'];
const ARMOR_SLOTS  = ['Helmet', 'Gauntlets', 'Chest', 'Legs', 'Class Item'];

export function Dashboard() {
  const [activeTab, setActiveTab] = useState<'roster' | 'advisor' | 'guide' | 'vault' | 'fireside' | 'capsule' | 'weekly' | 'lookup'>('roster');
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedCharId, setSelectedCharId] = useState<string | null>(null);
  const [loadoutLoading, setLoadoutLoading] = useState(false);
  const [loadoutError, setLoadoutError] = useState<string | null>(null);

  // Lore chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatStreaming, setChatStreaming] = useState(false);
  const [chatMode, setChatMode] = useState<'story' | 'tldr'>('story');
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Capsule state
  const [capsuleData, setCapsuleData] = useState<CapsuleData | null>(null);
  const [capsuleLoading, setCapsuleLoading] = useState(false);
  const [capsuleError, setCapsuleError] = useState<string | null>(null);

  // Swap panel state
  const [swapItem, setSwapItem] = useState<GearItem | null>(null);

  const navigate = useNavigate();
  const { accessToken, displayName, primaryMembership, logout, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated()) navigate('/');
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (activeTab !== 'roster' || !accessToken || !primaryMembership) return;

    if (characters.length > 0 && characters.some(c => c.gear.length > 0)) return;

    const fetchLoadout = async () => {
      setLoadoutLoading(true);
      setLoadoutError(null);
      try {
        const { membershipType, membershipId } = primaryMembership;
        const res = await fetch(
          `/api/loadout?membership_type=${membershipType}&membership_id=${membershipId}`,
          { headers: { Authorization: `Bearer ${accessToken}` } }
        );
        if (!res.ok) throw new Error(`Loadout fetch failed: ${res.status}`);
        const data = await res.json();
        setCharacters(data.characters);
        if (data.characters.length > 0) setSelectedCharId(data.characters[0].characterId);
      } catch (err: any) {
        setLoadoutError(err.message ?? 'Failed to load loadout.');
      } finally {
        setLoadoutLoading(false);
      }
    };

    fetchLoadout();
  }, [activeTab, accessToken, primaryMembership, characters.length]);

  useEffect(() => {
    if (activeTab !== 'capsule' || capsuleData || !accessToken || !primaryMembership) return;
    const fetch_capsule = async () => {
      setCapsuleLoading(true);
      setCapsuleError(null);
      try {
        const { membershipType, membershipId } = primaryMembership;
        const name = encodeURIComponent(
          primaryMembership.bungieGlobalDisplayName ?? primaryMembership.displayName ?? 'Guardian'
        );
        const res = await fetch(
          `/api/capsule?membership_type=${membershipType}&membership_id=${membershipId}&guardian_name=${name}`,
          { headers: { Authorization: `Bearer ${accessToken}` } }
        );
        if (!res.ok) throw new Error(`Capsule fetch failed: ${res.status}`);
        setCapsuleData(await res.json());
      } catch (err: any) {
        setCapsuleError(err.message ?? 'Failed to load capsule.');
      } finally {
        setCapsuleLoading(false);
      }
    };
    fetch_capsule();
  }, [activeTab, accessToken, primaryMembership, capsuleData]);

  const handleLogout = () => { logout(); navigate('/'); };

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const sendChat = async () => {
    const text = chatInput.trim();
    if (!text || chatStreaming || !accessToken) return;

    const history = chatMessages.map(({ role, content }) => ({ role, content }));
    setChatMessages((prev) => [...prev, { role: 'user', content: text }]);
    setChatInput('');
    setChatStreaming(true);

    // placeholder assistant message we'll stream into
    setChatMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ message: text, history, mode: chatMode }),
      });

      if (!res.ok || !res.body) throw new Error(`Chat failed: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let sources: { name: string; hash: string }[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.text) {
              setChatMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: updated[updated.length - 1].content + payload.text,
                };
                return updated;
              });
            }
            if (payload.done) {
              sources = payload.sources ?? [];
            }
          } catch {}
        }
      }

      if (sources.length) {
        setChatMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...updated[updated.length - 1], sources };
          return updated;
        });
      }
    } catch (err: any) {
      setChatMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: `Error: ${err.message}`,
        };
        return updated;
      });
    } finally {
      setChatStreaming(false);
    }
  };

  const guardianName = primaryMembership?.bungieGlobalDisplayName ?? primaryMembership?.displayName ?? displayName;
  const selectedChar = characters.find((c) => c.characterId === selectedCharId);

  return (
    <div className="min-h-screen p-4 md:p-10 md:pl-24 bg-linear-to-br from-transparent to-slate-900/50">

      <header className="mb-6 md:mb-10 border-b border-white/10 pb-4">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-2xl md:text-3xl font-bold font-cinzel text-destiny-accent drop-shadow-[0_0_10px_rgba(212,175,55,0.4)]">
            OrbitOps<span className="text-slate-500 ml-2 font-rajdhani">// Terminal</span>
          </h1>
          <div className="flex items-center gap-4">
            {guardianName && (
              <div className="text-right">
                <p className="text-xs text-slate-500 uppercase tracking-widest">Guardian</p>
                <p className="font-rajdhani font-semibold text-white tracking-wide">{guardianName}</p>
              </div>
            )}
            <button onClick={handleLogout} title="Log out" className="p-2 text-slate-500 hover:text-destiny-accent transition-colors">
              <LogOut size={18} />
            </button>
          </div>
        </div>
        <nav className="flex space-x-4 items-end overflow-x-auto pb-1">
          {(['roster', 'advisor', 'guide', 'vault', 'fireside', 'capsule', 'weekly', 'lookup'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'uppercase tracking-widest text-sm pb-2 font-rajdhani transition-all border-b-2 shrink-0',
                activeTab === tab
                  ? 'text-white border-destiny-accent'
                  : 'text-slate-500 border-transparent hover:text-slate-300'
              )}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>

      <main className="max-w-7xl">

        {/* ── ROSTER TAB ── */}
        {activeTab === 'roster' && (
          <div>
            {loadoutLoading && (
              <div className="flex items-center gap-3 text-slate-400 py-16 justify-center">
                <Loader2 className="animate-spin" size={20} />
                <span className="font-rajdhani tracking-widest uppercase">Loading loadout...</span>
              </div>
            )}

            {loadoutError && (
              <p className="text-red-400 text-sm py-8 text-center">{loadoutError}</p>
            )}

            {!loadoutLoading && !loadoutError && characters.length > 0 && (
              <div>
                {/* Character tabs */}
                <div className="flex gap-2 mb-8">
                  {characters.map((char) => (
                    <button
                      key={char.characterId}
                      onClick={() => setSelectedCharId(char.characterId)}
                      className={cn(
                        'relative overflow-hidden flex flex-col items-start px-5 py-3 border transition-all clip-chamfer',
                        selectedCharId === char.characterId
                          ? 'border-destiny-accent bg-destiny-panel'
                          : 'border-destiny-border bg-destiny-panel/50 hover:border-slate-500'
                      )}
                      style={char.emblemBackgroundPath ? {
                        backgroundImage: `linear-gradient(to right, rgba(15,23,42,0.9), rgba(15,23,42,0.7)), url(https://www.bungie.net${char.emblemBackgroundPath})`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                      } : undefined}
                    >
                      <span className={cn('font-cinzel text-sm font-bold', CLASS_COLORS[char.className] ?? 'text-white')}>
                        {char.className}
                      </span>
                      <span className="font-rajdhani text-xs text-destiny-accent tracking-widest">
                        ✦ {char.light}
                      </span>
                      {char.subclassName && (
                        <span className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-500">
                          {char.subclassName}
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Gear grid */}
                {selectedChar && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Weapons */}
                    <div>
                      <h3 className="font-rajdhani uppercase tracking-widest text-xs text-slate-500 mb-3">Weapons</h3>
                      <div className="flex flex-col gap-2">
                        {selectedChar.gear
                          .filter((g) => WEAPON_SLOTS.includes(g.slot))
                          .map((item) => <GearCard key={item.itemHash} item={item} onSwapClick={setSwapItem} />)}
                      </div>
                    </div>

                    {/* Armor */}
                    <div>
                      <h3 className="font-rajdhani uppercase tracking-widest text-xs text-slate-500 mb-3">Armor</h3>
                      <div className="flex flex-col gap-2">
                        {selectedChar.gear
                          .filter((g) => ARMOR_SLOTS.includes(g.slot))
                          .map((item) => <GearCard key={item.itemHash} item={item} onSwapClick={setSwapItem} />)}
                      </div>
                    </div>

                    {/* Ghost + Ship */}
                    {(['Ghost', 'Ship'] as const).map(slotName => {
                      const items = selectedChar.gear.filter(g => g.slot === slotName);
                      if (!items.length) return null;
                      return (
                        <div key={slotName} className="lg:col-span-2">
                          <h3 className="font-rajdhani uppercase tracking-widest text-xs text-slate-500 mb-3">{slotName}</h3>
                          {items.map(item => <GearCard key={item.itemHash} item={item} onSwapClick={setSwapItem} />)}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Swap panel */}
                {swapItem && primaryMembership && accessToken && (
                  <SwapPanel
                    equippedItem={swapItem}
                    membershipType={primaryMembership.membershipType}
                    membershipId={primaryMembership.membershipId}
                    accessToken={accessToken}
                    onClose={() => setSwapItem(null)}
                    onEquipped={() => {
                      setSwapItem(null);
                      setCharacters([]);  // triggers loadout re-fetch via useEffect
                    }}
                  />
                )}

                {/* Recent activity */}
                {primaryMembership && accessToken && (
                  <RecentActivity
                    membershipType={primaryMembership.membershipType}
                    membershipId={primaryMembership.membershipId}
                    accessToken={accessToken}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {/* ── ADVISOR TAB ── */}
        {activeTab === 'advisor' && primaryMembership && accessToken && (
          <FireteamAdvisor
            membershipType={primaryMembership.membershipType}
            membershipId={primaryMembership.membershipId}
            accessToken={accessToken}
          />
        )}

        {/* ── GUIDE TAB ── */}
        {activeTab === 'guide' && primaryMembership && accessToken && (
          <Pathfinder
            membershipType={primaryMembership.membershipType}
            membershipId={primaryMembership.membershipId}
            accessToken={accessToken}
            onOpenAdvisor={(activityId) => {
              setActiveTab('advisor');
              // FireteamAdvisor reads its own activity list on mount; pre-selection
              // is handled via sessionStorage so the component can pick it up.
              sessionStorage.setItem('pathfinder_activity', activityId);
            }}
          />
        )}

        {/* ── VAULT TAB ── */}
        {activeTab === 'vault' && primaryMembership && accessToken && (
          <VaultCleaner
            membershipType={primaryMembership.membershipType}
            membershipId={primaryMembership.membershipId}
            accessToken={accessToken}
          />
        )}

        {/* ── FIRESIDE TAB ── */}
        {activeTab === 'fireside' && (
          <div className="flex flex-col h-[calc(100vh-220px)]">

            {/* Header */}
            <div className="mb-6">
              <div className="flex items-baseline gap-3 mb-2">
                <h2 className="font-cinzel text-lg text-amber-200/70 tracking-wider">Fireside</h2>
                <span className="font-rajdhani text-[11px] text-amber-700/50 uppercase tracking-[0.2em]">
                  // Ghost Signal Active
                </span>
              </div>
              <div className="h-px w-full bg-linear-to-r from-amber-700/50 via-amber-900/20 to-transparent" />
            </div>

            {/* Message list */}
            <div className="flex-1 overflow-y-auto space-y-6 pr-1 mb-4">
              {chatMessages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center gap-4">
                  <div className="flex gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-700/50 animate-pulse" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-700/30 animate-pulse" style={{ animationDelay: '300ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-700/50 animate-pulse" style={{ animationDelay: '600ms' }} />
                  </div>
                  <p className="font-cinzel text-[11px] tracking-[0.3em] uppercase text-amber-800/60">
                    Your Ghost is listening
                  </p>
                  <p className="font-inter text-xs text-slate-600 max-w-xs leading-relaxed">
                    Ask about a weapon, a Guardian, a place. There's no rush. The fire's warm.
                  </p>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div key={i} className={cn('flex flex-col', msg.role === 'user' ? 'items-end' : 'items-start')}>
                  <span className={cn(
                    'text-[10px] tracking-[0.2em] uppercase mb-1.5 font-rajdhani',
                    msg.role === 'user' ? 'text-destiny-accent/40' : 'text-amber-600/50'
                  )}>
                    {msg.role === 'user' ? 'Guardian' : 'Ghost'}
                  </span>
                  <div className={cn(
                    'max-w-2xl px-5 py-4 font-inter text-sm leading-relaxed',
                    msg.role === 'user'
                      ? 'bg-destiny-accent/[0.07] border border-destiny-accent/20 text-slate-200 clip-chamfer'
                      : 'bg-destiny-ember border border-destiny-ember-border text-amber-50/80 clip-chamfer-reverse'
                  )}>
                    {msg.role === 'assistant' && !msg.content && chatStreaming && (
                      <span className="inline-flex gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-600/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-600/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-600/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                      </span>
                    )}
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-amber-800/20 flex flex-wrap gap-x-3 gap-y-1">
                        <span className="text-[10px] text-amber-800/50 font-rajdhani uppercase tracking-widest w-full mb-0.5">
                          Recovered fragments
                        </span>
                        {msg.sources.map((s) => (
                          <span key={s.hash} className="text-[11px] text-amber-700/60 font-inter italic">
                            {s.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatBottomRef} />
            </div>

            {/* Input row */}
            <div className="flex flex-col gap-1">
              <div className="flex border border-amber-900/30 overflow-hidden self-start md:hidden">
                {(['story', 'tldr'] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setChatMode(m)}
                    className={cn(
                      'px-3 py-2 font-rajdhani text-[11px] uppercase tracking-widest transition-colors',
                      chatMode === m
                        ? 'bg-amber-900/40 text-amber-400'
                        : 'bg-destiny-panel text-amber-800/50 hover:text-amber-700/70'
                    )}
                  >
                    {m === 'tldr' ? 'TL;DR — Quick answer' : 'Story — Full lore'}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendChat()}
                  placeholder="Speak, Guardian…"
                  disabled={chatStreaming}
                  className="flex-1 bg-destiny-panel border border-amber-900/30 text-slate-200 placeholder-amber-900/40 font-inter px-4 py-3 text-sm focus:outline-none focus:border-amber-700/50 transition-colors disabled:opacity-50"
                />
                <div className="hidden md:flex border border-amber-900/30 overflow-hidden">
                  {(['story', 'tldr'] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setChatMode(m)}
                      className={cn(
                        'px-3 py-3 font-rajdhani text-[11px] uppercase tracking-widest transition-colors',
                        chatMode === m
                          ? 'bg-amber-900/40 text-amber-400'
                          : 'bg-destiny-panel text-amber-800/50 hover:text-amber-700/70'
                      )}
                    >
                      {m}
                    </button>
                  ))}
                </div>
                <button
                  onClick={sendChat}
                  disabled={chatStreaming || !chatInput.trim()}
                  className="px-4 py-3 bg-destiny-ember border border-destiny-ember-border text-amber-500/70 hover:text-amber-400 hover:bg-amber-900/40 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {chatStreaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── CAPSULE TAB ── */}
        {activeTab === 'capsule' && primaryMembership && accessToken && (
          <div className="space-y-16">
            {/* Stats dashboard — front and centre */}
            <StatsDashboard
              membershipType={primaryMembership.membershipType}
              membershipId={primaryMembership.membershipId}
              accessToken={accessToken}
            />

            {/* Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-white/6" />
              <span className="font-rajdhani text-[9px] uppercase tracking-widest text-slate-700">Time Capsule</span>
              <div className="flex-1 h-px bg-white/6" />
            </div>

            {/* Capsule narrative */}
            {capsuleLoading && (
              <div className="flex flex-col items-center justify-center py-16 gap-4 text-slate-500">
                <Loader2 className="animate-spin" size={24} />
                <div className="text-center">
                  <p className="font-rajdhani uppercase tracking-widest text-sm">Compiling your record…</p>
                  <p className="font-inter text-xs text-slate-600 mt-1">Fetching stats and generating your Ghost's message</p>
                </div>
              </div>
            )}
            {capsuleError && (
              <p className="text-red-400 text-sm py-8 text-center font-rajdhani">{capsuleError}</p>
            )}
            {!capsuleLoading && !capsuleError && capsuleData && (
              <TimeCapsule data={capsuleData} />
            )}
          </div>
        )}

        {/* ── WEEKLY TAB ── */}
        {activeTab === 'weekly' && <WeeklyReset />}

        {/* ── LOOKUP TAB ── */}
        {activeTab === 'lookup' && <PlayerSearch />}

      </main>
    </div>
  );
}
