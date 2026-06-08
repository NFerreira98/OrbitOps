import os
import zipfile
import httpx
import aiosqlite
import asyncio
from pathlib import Path

BUNGIE_ROOT = "https://www.bungie.net"
DATA_DIR = Path(__file__).parent.parent.parent / "data"

class ManifestManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._db_path: Path | None = None

    @property
    def db_path(self) -> Path | None:
        if self._db_path is None:
            existing = sorted(DATA_DIR.glob("*.content"))
            self._db_path = existing[0] if existing else None
        return self._db_path

    @db_path.setter
    def db_path(self, value: Path | None) -> None:
        self._db_path = value
        
    async def get_manifest_info(self):
        async with httpx.AsyncClient() as client:
            headers = {"X-API-Key": os.getenv("BUNGIE_API_KEY", "")}
            res = await client.get(f"{BUNGIE_ROOT}/Platform/Destiny2/Manifest/", headers=headers)
            res.raise_for_status()
            return res.json()["Response"]
            
    async def init_manifest(self):
        print("Checking Destiny 2 manifest...")
        try:
            manifest_info = await self.get_manifest_info()
            mobile_world_content_path = manifest_info["mobileWorldContentPaths"]["en"]
            file_name = mobile_world_content_path.split("/")[-1]
            
            local_zip_path = DATA_DIR / f"{file_name}.zip"
            self.db_path = DATA_DIR / file_name
            
            # If the database file is already there, we assume it's up to date for now
            if self.db_path.exists():
                print(f"Manifest already exists at {self.db_path}")
                return
            
            print(f"Downloading manifest from {BUNGIE_ROOT}{mobile_world_content_path}...")
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
                async with client.stream("GET", f"{BUNGIE_ROOT}{mobile_world_content_path}") as r:
                    r.raise_for_status()
                    with open(local_zip_path, "wb") as f:
                        async for chunk in r.aiter_bytes():
                            f.write(chunk)

            print("Extracting manifest...")
            with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                zip_ref.extractall(DATA_DIR)

            os.remove(local_zip_path)
            print("Manifest downloaded and extracted successfully.")
        except Exception as e:
            print(f"ERROR: Failed to initialize manifest: {e}")
            raise
            
    async def get_lore(self, lore_hash: int):
        if not self.db_path:
            return None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinyLoreDefinition WHERE id = ? OR id = ?",
                (lore_hash, lore_hash - 4294967296),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_all_season_definitions(self):
        """Return all season definitions with a positive seasonNumber (for capsule timeline)."""
        if not self.db_path:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinySeasonDefinition "
                "WHERE CAST(json_extract(json, '$.seasonNumber') AS INTEGER) > 0"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_all_items_with_flavor(self):
        """Return JSON rows for items that have non-empty flavorText."""
        if not self.db_path:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinyInventoryItemDefinition "
                "WHERE json_extract(json, '$.flavorText') IS NOT NULL "
                "AND json_extract(json, '$.flavorText') != ''"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_all_activities_with_description(self):
        """Return JSON rows for activities that have a non-trivial description."""
        if not self.db_path:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinyActivityDefinition "
                "WHERE length(json_extract(json, '$.displayProperties.description')) > 80"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_all_seasons(self):
        """Return JSON rows for all season definitions that have a description."""
        if not self.db_path:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinySeasonDefinition "
                "WHERE json_extract(json, '$.displayProperties.description') IS NOT NULL "
                "AND json_extract(json, '$.displayProperties.description') != ''"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_all_lore(self):
        if not self.db_path:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT json FROM DestinyLoreDefinition")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_record(self, record_hash: int):
        if not self.db_path:
            return None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinyRecordDefinition WHERE id = ? OR id = ?",
                (record_hash, record_hash - 4294967296),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_item(self, item_hash: int):
        if not self.db_path:
            return None

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinyInventoryItemDefinition WHERE id = ? OR id = ?",
                (item_hash, item_hash - 4294967296) # Handle signed 32-bit int cast
            )
            row = await cursor.fetchone()
            if row:
                return row[0]
            return None

    async def get_items_batch(self, hashes: list[int]) -> list[str]:
        """Batch-fetch item definitions for a list of hashes. Returns raw JSON strings."""
        if not self.db_path or not hashes:
            return []
        # Each hash needs its signed-int counterpart to handle Bungie's 32-bit cast
        all_ids: list[int] = []
        for h in hashes:
            all_ids.append(h)
            signed = h - 4294967296
            if signed != h:
                all_ids.append(signed)
        placeholders = ",".join("?" * len(all_ids))
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"SELECT json FROM DestinyInventoryItemDefinition WHERE id IN ({placeholders})",
                tuple(all_ids),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_activity(self, activity_hash: int) -> str | None:
        if not self.db_path:
            return None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinyActivityDefinition WHERE id = ? OR id = ?",
                (activity_hash, activity_hash - 4294967296),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_catalog_items(
        self,
        tier: int,
        item_type: int | None = None,
        class_type: int | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """Fetch catalog items by tier (5=Legendary, 6=Exotic) with optional filters.
        Returns lightweight dicts extracted from the manifest (no full JSON blobs)."""
        if not self.db_path:
            return []

        conditions = [
            "json_extract(json, '$.inventory.tierType') = ?",
            "json_extract(json, '$.itemType') IN (2, 3)",
            "json_extract(json, '$.displayProperties.name') IS NOT NULL",
            "json_extract(json, '$.displayProperties.name') != ''",
            "json_extract(json, '$.displayProperties.name') != 'Classified'",
            "(json_extract(json, '$.redacted') IS NULL OR json_extract(json, '$.redacted') = 0)",
            "json_extract(json, '$.displayProperties.hasIcon') = 1",
        ]
        params: list = [tier]

        if item_type is not None:
            conditions.append("json_extract(json, '$.itemType') = ?")
            params.append(item_type)

        if class_type is not None:
            conditions.append(
                "(json_extract(json, '$.classType') = ? OR json_extract(json, '$.classType') = 3)"
            )
            params.append(class_type)

        if search:
            conditions.append(
                "json_extract(json, '$.displayProperties.name') LIKE ?"
            )
            params.append(f"%{search}%")

        where = " AND ".join(conditions)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"""SELECT
                    CAST(json_extract(json, '$.hash') AS INTEGER),
                    json_extract(json, '$.displayProperties.name'),
                    json_extract(json, '$.displayProperties.icon'),
                    json_extract(json, '$.flavorText'),
                    CAST(json_extract(json, '$.inventory.tierType') AS INTEGER),
                    CAST(json_extract(json, '$.itemType') AS INTEGER),
                    CAST(json_extract(json, '$.itemSubType') AS INTEGER),
                    CAST(json_extract(json, '$.classType') AS INTEGER),
                    CAST(json_extract(json, '$.collectibleHash') AS INTEGER)
                FROM DestinyInventoryItemDefinition WHERE {where}""",
                tuple(params),
            )
            rows = await cursor.fetchall()
        return [
            {
                "hash": row[0],
                "name": row[1] or "",
                "icon": row[2],
                "flavorText": row[3],
                "tierType": row[4],
                "itemType": row[5],
                "itemSubType": row[6] or 0,
                "classType": row[7] if row[7] is not None else 3,
                "collectibleHash": row[8] or None,
            }
            for row in rows
            if row[0]
        ]

    async def get_all_collectibles_with_source(self) -> dict[int, str]:
        """Return {hash: sourceString} for all collectibles that have sourceString."""
        if not self.db_path:
            return {}
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT
                    CAST(json_extract(json, '$.hash') AS INTEGER),
                    json_extract(json, '$.sourceString')
                FROM DestinyCollectibleDefinition
                WHERE json_extract(json, '$.sourceString') IS NOT NULL
                AND json_extract(json, '$.sourceString') != ''"""
            )
            rows = await cursor.fetchall()
        return {int(row[0]): row[1] for row in rows if row[0] and row[1]}

    async def get_milestone(self, milestone_hash: int) -> str | None:
        if not self.db_path:
            return None
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT json FROM DestinyMilestoneDefinition WHERE id = ? OR id = ?",
                (milestone_hash, milestone_hash - 4294967296),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_milestones_batch(self, hashes: list[int]) -> list[str]:
        if not self.db_path or not hashes:
            return []
        all_ids: list[int] = []
        for h in hashes:
            all_ids.append(h)
            signed = h - 4294967296
            if signed != h:
                all_ids.append(signed)
        placeholders = ",".join("?" * len(all_ids))
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"SELECT json FROM DestinyMilestoneDefinition WHERE id IN ({placeholders})",
                tuple(all_ids),
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
