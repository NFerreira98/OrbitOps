export interface PathfinderReward {
  name: string;
  iconUrl: string | null;
  acquired: boolean;
  clipUrl: string;
}

export interface PathfinderEntry {
  id: string;
  name: string;
  category: 'raid' | 'dungeon' | 'exotic-mission';
  difficulty: number;
  imageUrl: string | null;
  description: string;
  rewards: PathfinderReward[];
  tags: string[];
}
