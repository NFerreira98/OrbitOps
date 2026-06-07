import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface DestinyMembership {
  membershipType: number;
  membershipId: string;
  displayName: string;
  bungieGlobalDisplayName?: string;
  bungieGlobalDisplayNameCode?: number;
}

interface AuthState {
  accessToken: string | null;
  displayName: string | null;
  primaryMembership: DestinyMembership | null;
  allMemberships: DestinyMembership[];
  setAuth: (data: {
    accessToken: string;
    displayName: string | null;
    primaryMembership: DestinyMembership | null;
    allMemberships: DestinyMembership[];
  }) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      displayName: null,
      primaryMembership: null,
      allMemberships: [],
      setAuth: (data) => set({
        accessToken: data.accessToken,
        displayName: data.displayName,
        primaryMembership: data.primaryMembership,
        allMemberships: data.allMemberships,
      }),
      logout: () => set({
        accessToken: null,
        displayName: null,
        primaryMembership: null,
        allMemberships: [],
      }),
      isAuthenticated: () => !!get().accessToken,
    }),
    { name: 'orbitops-auth' }
  )
);
