export interface TimelinePoint {
  month: string;
  era: string;
  pve: number;
  pvp: number;
  gambit: number;
}

export interface ActivityEntry {
  activityHash: number;
  name: string;
  imageUrl: string | null;
  completions: number;
  fastestMs: number | null;
  kills: number;
  mode: 'raid' | 'dungeon' | 'strike' | 'pvp' | 'gambit' | 'exotic-mission' | 'misc';
}

export interface WeaponBucket {
  weaponType: string;
  kills: number;
  pct: number;
}

export interface ModeBlock {
  mode: string;
  label: string;
  hoursPlayed: number;
  kills: number;
  activitiesEntered: number;
  winRate: number | null;
}

export interface ContextualStat {
  label: string;
  raw: string;
  frame: string;
}

export interface PvpStats {
  kd: number;
  kda: number;
  efficiency: number;
  combatRating: number;
  totalKills: number;
  totalDeaths: number;
  totalAssists: number;
  activitiesEntered: number;
  activitiesWon: number;
  precisionKills: number;
  precisionPct: number;
  bestSingleGameKills: number;
  longestKillSpree: number;
  longestLifeSecs: number;
  winRate: number;
  orbsDropped: number;
  resurrectionsPerformed: number;
  resurrectionsReceived: number;
}

export interface AbilityStats {
  superKills: number;
  grenadeKills: number;
  meleeKills: number;
  gunKills: number;
  superPct: number;
  grenadePct: number;
  meleePct: number;
  gunPct: number;
  totalKills: number;
}

export interface StatsDashboardResponse {
  cached: boolean;
  modes: ModeBlock[];
  timeline: TimelinePoint[];
  topActivities: ActivityEntry[];
  weaponBuckets: WeaponBucket[];
  contextualStats: ContextualStat[];
  pvpStats: PvpStats | null;
  abilityStats: AbilityStats | null;
}
