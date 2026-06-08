import os
import base64
import httpx
from fastapi import HTTPException
from urllib.parse import urlencode

BUNGIE_ROOT = "https://www.bungie.net"

class BungieAPI:
    def __init__(self):
        self.api_key = os.getenv("BUNGIE_API_KEY")
        self.client_id = os.getenv("BUNGIE_CLIENT_ID")
        self.client_secret = os.getenv("BUNGIE_CLIENT_SECRET")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        self.redirect_uri = f"{frontend_url}/auth/callback"

    def get_auth_url(self) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
        }
        return f"{BUNGIE_ROOT}/en/OAuth/Authorize?{urlencode(params)}"

    async def get_token(self, code: str) -> dict:
        b64_auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{BUNGIE_ROOT}/Platform/App/OAuth/Token/", headers=headers, data=data)
            if res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Token exchange failed: {res.text}")
            return res.json()

    async def get_memberships(self, access_token: str) -> dict:
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/User/GetMembershipsForCurrentUser/",
                headers=headers,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def get_profile(self, membership_type: int, destiny_membership_id: str, access_token: str, components: str = "200,205"):
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Profile/{destiny_membership_id}/?components={components}",
                headers=headers,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def get_collectibles(self, membership_type: int, destiny_membership_id: str, access_token: str) -> dict:
        """Collectibles (800, 900) + inventory/equipment (102, 201, 205) for reliable exotic ownership checks."""
        return await self.get_profile(membership_type, destiny_membership_id, access_token, components="102,200,201,205,800,900")

    async def get_vault_full(self, membership_type: int, destiny_membership_id: str, access_token: str):
        """Vault + bag items with per-instance power levels (300) and socket/perk data (305)."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        components = "102,200,201,300,305"
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Profile/{destiny_membership_id}/?components={components}",
                headers=headers,
                timeout=25.0,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def transfer_item(
        self,
        item_reference_hash: int,
        instance_id: str,
        character_id: str,
        membership_type: int,
        access_token: str,
    ) -> None:
        """Move an item from the vault to a character's inventory."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "itemReferenceHash": item_reference_hash,
            "stackSize": 1,
            "transferToVault": False,
            "itemId": instance_id,
            "characterId": character_id,
            "membershipType": membership_type,
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{BUNGIE_ROOT}/Platform/Destiny2/Actions/Items/TransferItem/",
                headers=headers,
                json=body,
                timeout=15.0,
            )
            res.raise_for_status()

    async def equip_item(
        self,
        instance_id: str,
        character_id: str,
        membership_type: int,
        access_token: str,
    ) -> None:
        """Equip an item that is already in the character's inventory."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "itemId": instance_id,
            "characterId": character_id,
            "membershipType": membership_type,
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{BUNGIE_ROOT}/Platform/Destiny2/Actions/Items/EquipItem/",
                headers=headers,
                json=body,
                timeout=15.0,
            )
            res.raise_for_status()

    async def get_profile_with_vault(self, membership_type: int, destiny_membership_id: str, access_token: str):
        """Same as get_profile but also fetches vault (102) and character bags (201)."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        # 102 = profileInventory (vault), 200 = characters, 201 = characterInventories (bags), 205 = equipped
        components = "102,200,201,205"
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Profile/{destiny_membership_id}/?components={components}",
                headers=headers,
                timeout=20.0,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def get_historical_stats(self, membership_type: int, destiny_membership_id: str, access_token: str) -> dict:
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}/Stats/",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def get_activity_history(
        self,
        membership_type: int,
        destiny_membership_id: str,
        character_id: str,
        access_token: str,
        mode: int = 4,
        count: int = 250,
        page: int = 0,
    ) -> dict:
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}"
                f"/Character/{character_id}/Stats/Activities/"
                f"?mode={mode}&count={count}&page={page}",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_monthly_stats(
        self,
        membership_type: int,
        destiny_membership_id: str,
        character_id: str,
        access_token: str,
    ) -> dict:
        """Monthly PvE activity counts per character — used to build the era activity chart."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}"
                f"/Character/{character_id}/Stats/?modes=7&periodType=2&groups=1",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_character_stats(
        self,
        membership_type: int,
        destiny_membership_id: str,
        character_id: str,
        access_token: str,
    ) -> dict:
        """Per-character stats with explicit modes. The account-level endpoint only returns
        allPvE/allPvP; this endpoint exposes raid, nightfall, allStrikes etc."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        modes = "4,16,17,18,46,47"
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}"
                f"/Character/{character_id}/Stats/?modes={modes}",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def search_by_name_prefix(self, prefix: str, page: int = 0) -> list[dict]:
        """Search players by display name prefix — public, no auth needed."""
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{BUNGIE_ROOT}/Platform/User/Search/GlobalName/{page}/",
                headers=headers,
                json={"displayNamePrefix": prefix},
                timeout=10.0,
            )
            print(f"[bungie-search] status={res.status_code} prefix={prefix!r}")
            if res.status_code != 200:
                print(f"[bungie-search] body={res.text[:300]}")
                return []
            return res.json().get("Response", {}).get("searchResults", [])

    async def search_player_by_bungie_name(
        self,
        display_name: str,
        display_name_code: int,
    ) -> dict | None:
        """Search for a player by Bungie name + code (e.g. 'Guardian', 1234).
        Returns the cross-save primary membership, or the first result, or None."""
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{BUNGIE_ROOT}/Platform/Destiny2/SearchDestinyPlayerByBungieName/-1/",
                headers=headers,
                json={"displayName": display_name, "displayNameCode": display_name_code},
                timeout=10.0,
            )
            if res.status_code != 200:
                return None
            results: list[dict] = res.json().get("Response", [])
            if not results:
                return None
            cross_save = next((r for r in results if r.get("crossSaveOverride", 0) != 0), None)
            return cross_save or results[0]

    async def get_public_equipment(self, membership_type: int, membership_id: str) -> dict:
        """Fetch character + equipment data for any public profile (API key only, no OAuth)."""
        headers = {"X-API-Key": self.api_key}
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Profile/{membership_id}/"
                "?components=200,205",
                headers=headers,
                timeout=15.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_pgcr(self, instance_id: str) -> dict:
        """Post-Game Carnage Report — lists every player in a completed activity instance.
        Public endpoint; only needs API key, no auth token."""
        headers = {"X-API-Key": self.api_key}
        async with httpx.AsyncClient(follow_redirects=True) as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/Stats/PostGameCarnageReport/{instance_id}/",
                headers=headers,
                timeout=15.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_lifetime_mode_stats(
        self,
        membership_type: int,
        destiny_membership_id: str,
        character_id: str,
        access_token: str,
    ) -> dict:
        """AllTime stats for allPvE(7), allPvP(5), Gambit(63) — no periodType so we get allTime."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}"
                f"/Character/{character_id}/Stats/?modes=7,5,63",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_monthly_stats_modes(
        self,
        membership_type: int,
        destiny_membership_id: str,
        character_id: str,
        access_token: str,
        modes: str = "7,5,63",
    ) -> dict:
        """Monthly activity counts broken down by mode: allPvE(7), allPvP(5), Gambit(63)."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}"
                f"/Character/{character_id}/Stats/?modes={modes}&periodType=2&groups=1",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_aggregate_activity_stats(
        self,
        membership_type: int,
        destiny_membership_id: str,
        character_id: str,
        access_token: str,
    ) -> dict:
        """Per-activity lifetime completions, kills, fastest time — used for the activity leaderboard."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}"
                f"/Character/{character_id}/Stats/AggregateActivityStats/",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_character_weapons_stats(
        self,
        membership_type: int,
        destiny_membership_id: str,
        character_id: str,
        access_token: str,
    ) -> dict:
        """Per-character stats with Weapons group (groups=2) for uniqueWeaponKills breakdown."""
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Account/{destiny_membership_id}"
                f"/Character/{character_id}/Stats/?groups=2",
                headers=headers,
                timeout=30.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})

    async def get_profile_summary(self, membership_type: int, destiny_membership_id: str, access_token: str) -> dict:
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        # 100 = profile metadata (dateLastPlayed), 200 = characters (titleRecordHash)
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Profile/{destiny_membership_id}/?components=100,200",
                headers=headers,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def get_public_milestones(self) -> dict:
        """Weekly milestones — public endpoint, API key only."""
        headers = {"X-API-Key": self.api_key}
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/Milestones/",
                headers=headers,
                timeout=15.0,
            )
            res.raise_for_status()
            return res.json().get("Response", {})
