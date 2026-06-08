export interface MemberProfile {
  displayName: string;
  className: string;
  subclassElement: string;
  exoticWeapon: string | null;
  exoticArmor: string | null;
  weaponElements: string[];
  isCurrentUser: boolean;
  error: string | null;
}

export interface TeamRole {
  label: string;
  role: string;
}

export interface EncounterCard {
  name: string;
  imageUrl: string | null;
  weaponTypes: string[];
  elements: string[];
  exotics: string[];
  tip: string;
  steps: string[];
  teams: TeamRole[];
  vaultMatches: string[];
}

export interface ActivityInfo {
  id: string;
  name: string;
  type: 'raid' | 'dungeon';
  imageUrl: string | null;
  videoUrl: string;
  encounters: EncounterCard[];
}

export interface FireteamAnalysis {
  members: MemberProfile[];
  elementCoverage: string[];
  missingElements: string[];
  classCoverage: string[];
  claudeAnalysis: string;
  encounterCards: EncounterCard[];
}
