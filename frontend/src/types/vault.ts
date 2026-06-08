export interface VaultWeaponCopy {
  instanceId: string;
  power: number;
  perks: string[];
  isMasterworked: boolean;
}

export interface VaultWeaponGroup {
  weaponHash: number;
  name: string;
  weaponType: string;
  element: string;
  isExotic: boolean;
  iconUrl: string | null;
  copies: VaultWeaponCopy[];
}
