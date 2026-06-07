export interface CharacterSummary {
  characterId: string;
  className: string;
  light: number;
  emblemPath: string | null;
  emblemBackgroundPath: string | null;
  isPrimary: boolean;
}

export interface SeasonEntry {
  hash: number;
  name: string;
  seasonNumber: number;
  era: string;
  description: string;
  wasActive: boolean;
}

export interface RaidBookend {
  firstCharacterDate: string | null;
  firstRaidDate: string | null;
  lastRaidDate: string | null;
  lastLoginDate: string | null;
  raidCount: number;
}

export interface MonthlyPoint {
  period: string;   // "YYYY-MM"
  era: string;
  activities: number;
}

export interface EraActivity {
  era: string;
  activities: number;
  relativeActivity: number;  // 0.0–1.0
  monthsActive: number;
}

export interface PrestigeAchievement {
  name: string;
  description: string;
  tier: number;  // 1–5
}

export interface CapsuleData {
  guardianName: string;
  platform: string;
  characters: CharacterSummary[];
  hoursPlayed: number;
  totalKills: number;
  totalDeaths: number;
  precisionKillPct: number;
  raidsCleared: number;
  nightfallsCleared: number;
  strikesCleared: number;
  pvpMatches: number;
  pvpWins: number;
  pvpKD: number;
  titles: string[];
  dateLastPlayed: string;
  ghostNarrative: string;
  seasons: SeasonEntry[];
  archetype: string;
  yearsActive: number;
  firstSeason: string;
  raidBookend: RaidBookend;
  eraActivity: EraActivity[];
  monthlyData: MonthlyPoint[];
  prestigeAchievement: PrestigeAchievement | null;
  verdict: string;
}
