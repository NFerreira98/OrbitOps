from __future__ import annotations
import asyncio
import json
from pydantic import BaseModel
from fastapi import APIRouter, Header, HTTPException

from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["pathfinder"])
bungie_api = BungieAPI()
manifest = ManifestManager()

# ── Static content guide ───────────────────────────────────────────────────────
# reward_hashes: list of {hash, clip_url} — item hash verified from manifest
# activity_hash: used to resolve pgcrImage from DestinyActivityDefinition

YT = "https://www.youtube.com/results?search_query="

CONTENT_GUIDE: list[dict] = [
    {
        "id": "vault-of-glass",
        "name": "Vault of Glass",
        "category": "raid",
        "difficulty": 3,
        "description": "The original Destiny raid, remade for Destiny 2. Manage oracles and relic mechanics across Venetian-glass arenas to slay Atheon, Time's Conflux.",
        "activity_hash": 3881495763,
        "rewards": [
            {"hash": 4289226715, "clip_url": YT + "Vex+Mythoclast+destiny+2+exotic"},  # Vex Mythoclast
        ],
        "tags": ["new-player", "raid-curious", "exotic-hunter"],
    },
    {
        "id": "crotas-end",
        "name": "Crota's End",
        "category": "raid",
        "difficulty": 3,
        "description": "Navigate the Hive's moon fortress in darkness and bring down Crota, Son of Oryx, using his own stolen Sword.",
        "activity_hash": 4179289725,
        "rewards": [
            {"hash": 1034055198, "clip_url": YT + "Necrochasm+destiny+2+exotic"},  # Necrochasm
        ],
        "tags": ["new-player", "raid-curious", "exotic-hunter"],
    },
    {
        "id": "kings-fall",
        "name": "King's Fall",
        "category": "raid",
        "difficulty": 4,
        "description": "Board Oryx's Dreadnaught and confront the Taken King himself in Destiny's most iconic raid, now rebuilt for D2.",
        "activity_hash": 1374392663,
        "rewards": [
            {"hash": 1802135586, "clip_url": YT + "Touch+of+Malice+destiny+2+exotic"},  # Touch of Malice
        ],
        "tags": ["raid-curious", "exotic-hunter", "returning"],
    },
    {
        "id": "last-wish",
        "name": "Last Wish",
        "category": "raid",
        "difficulty": 4,
        "description": "Infiltrate the Dreaming City and face Riven of a Thousand Voices, the last living Ahamkara, in the most mechanically complex raid in the game.",
        "activity_hash": 2122313384,
        "rewards": [
            {"hash": 2069224589, "clip_url": YT + "One+Thousand+Voices+destiny+2+exotic"},  # One Thousand Voices
        ],
        "tags": ["raid-curious", "exotic-hunter", "returning"],
    },
    {
        "id": "garden-of-salvation",
        "name": "Garden of Salvation",
        "category": "raid",
        "difficulty": 4,
        "description": "Explore the Black Garden and tether the Consecrated Mind to ultimately face the Sanctified Mind. Divinity is an S-tier support exotic unique to this raid.",
        "activity_hash": 2659723068,
        "rewards": [
            {"hash": 4103414242, "clip_url": YT + "Divinity+exotic+destiny+2"},  # Divinity
        ],
        "tags": ["raid-curious", "exotic-hunter"],
    },
    {
        "id": "deep-stone-crypt",
        "name": "Deep Stone Crypt",
        "category": "raid",
        "difficulty": 3,
        "description": "A sci-fi raid set deep inside Europa's ice. Fight through Fallen Exo experiments and face Taniks, the Abomination, in zero-gravity. Eyes of Tomorrow is one of the best burst-damage rockets in the game.",
        "activity_hash": 3976949817,
        "rewards": [
            {"hash": 2399110176, "clip_url": YT + "Eyes+of+Tomorrow+destiny+2+exotic"},  # Eyes of Tomorrow
        ],
        "tags": ["raid-curious", "exotic-hunter", "returning"],
    },
    {
        "id": "vow-of-the-disciple",
        "name": "Vow of the Disciple",
        "category": "raid",
        "difficulty": 4,
        "description": "Enter Savathûn's Throne World pyramid and learn the Witness's symbol language. The raid teaches its own communication system — and Collective Obligation copies enemy debuffs.",
        "activity_hash": 1441982566,
        "rewards": [
            {"hash": 3505113722, "clip_url": YT + "Collective+Obligation+destiny+2+exotic"},  # Collective Obligation
        ],
        "tags": ["raid-curious", "exotic-hunter", "returning"],
    },
    {
        "id": "root-of-nightmares",
        "name": "Root of Nightmares",
        "category": "raid",
        "difficulty": 3,
        "description": "Traverse the nightmare-infected Witness ship and end Nezarec, Final God of Pain. One of the more approachable modern raids for new fireteams.",
        "activity_hash": 2381413764,
        "rewards": [
            {"hash": 3371017761, "clip_url": YT + "Conditional+Finality+destiny+2+exotic"},  # Conditional Finality
        ],
        "tags": ["returning", "exotic-hunter", "raid-curious"],
    },
    {
        "id": "salvations-edge",
        "name": "Salvation's Edge",
        "category": "raid",
        "difficulty": 5,
        "description": "The most mechanically demanding raid in Destiny 2. Enter the Witness itself and use its own power against it. Requires flawless coordination.",
        "activity_hash": 1541433876,
        "rewards": [
            {"hash": 3284383335, "clip_url": YT + "Euphony+destiny+2+exotic"},  # Euphony
        ],
        "tags": ["returning", "raid-curious", "exotic-hunter"],
    },
    {
        "id": "desert-perpetual",
        "name": "The Desert Perpetual",
        "category": "raid",
        "difficulty": 4,
        "description": "The newest raid from the Edge of Fate expansion. Whirling Ovation is the unique exotic rocket launcher exclusive to this activity.",
        "activity_hash": 1044919065,
        "rewards": [
            {"hash": 1202007252, "clip_url": YT + "Whirling+Ovation+destiny+2+exotic"},  # Whirling Ovation
        ],
        "tags": ["returning", "raid-curious", "exotic-hunter"],
    },
    {
        "id": "shattered-throne",
        "name": "Shattered Throne",
        "category": "dungeon",
        "difficulty": 2,
        "description": "The first dungeon ever added to Destiny 2, set deep in the Dreaming City's cursed labyrinth. Atmospheric and lore-rich — a great introduction to the dungeon format. No exclusive exotic, but completing it is part of unlocking the Wish-Ender exotic bow.",
        "activity_hash": 2032534090,
        "rewards": [],
        "tags": ["new-player", "solo"],
    },
    {
        "id": "pit-of-heresy",
        "name": "Pit of Heresy",
        "category": "dungeon",
        "difficulty": 2,
        "description": "Descend into the Hive's Moon fortress across four brutal floors. No exclusive exotic drop, but completing it advances the Xenophage exotic quest — one of the most powerful machine guns in the game.",
        "activity_hash": 2582501063,
        "rewards": [],
        "tags": ["new-player", "solo"],
    },
    {
        "id": "prophecy",
        "name": "Prophecy",
        "category": "dungeon",
        "difficulty": 2,
        "description": "A free-to-play dungeon set in the domain of the Nine. Geometric puzzles and a hauntingly beautiful aesthetic. No exclusive exotic — but a great solo challenge for any player.",
        "activity_hash": 1077850348,
        "rewards": [],
        "tags": ["new-player", "solo"],
    },
    {
        "id": "grasp-of-avarice",
        "name": "Grasp of Avarice",
        "category": "dungeon",
        "difficulty": 3,
        "description": "A 30th Anniversary dungeon set in Destiny 1's original Loot Cave area. Complete the in-dungeon quest to earn Gjallarhorn — the most iconic exotic rocket launcher in franchise history.",
        "activity_hash": 4078656646,
        "rewards": [
            {"hash": 1363886209, "clip_url": YT + "Gjallarhorn+destiny+2+exotic+showcase"},  # Gjallarhorn
        ],
        "tags": ["solo", "exotic-hunter"],
    },
    {
        "id": "duality",
        "name": "Duality",
        "category": "dungeon",
        "difficulty": 3,
        "description": "Enter Caiatl's mindscape and battle through her memories. Heartshadow is an exotic sword that turns you invisible on kills — one of the most unique exotics in PvP and endgame PvE.",
        "activity_hash": 2823159265,
        "rewards": [
            {"hash": 3664831848, "clip_url": YT + "Heartshadow+destiny+2+exotic+sword"},  # Heartshadow
        ],
        "tags": ["solo", "exotic-hunter"],
    },
    {
        "id": "vespers-host",
        "name": "Vesper's Host",
        "category": "dungeon",
        "difficulty": 3,
        "description": "A dungeon set aboard Variks's prison station. Ice Breaker makes its legendary return as the exclusive exotic — the first self-recharging sniper rifle in Destiny history.",
        "activity_hash": 300092127,
        "rewards": [
            {"hash": 1111334348, "clip_url": YT + "Ice+Breaker+destiny+2+exotic+sniper"},  # Ice Breaker
        ],
        "tags": ["solo", "exotic-hunter", "returning"],
    },
    {
        "id": "equilibrium",
        "name": "Equilibrium",
        "category": "dungeon",
        "difficulty": 3,
        "description": "The newest dungeon from the Edge of Fate expansion. Heirloom is the exclusive exotic combat bow — earn it from the final boss.",
        "activity_hash": 2727361621,
        "rewards": [
            {"hash": 1685137410, "clip_url": YT + "Heirloom+destiny+2+exotic+bow"},  # Heirloom
        ],
        "tags": ["solo", "exotic-hunter", "returning"],
    },
    {
        "id": "spire-of-the-watcher",
        "name": "Spire of the Watcher",
        "category": "dungeon",
        "difficulty": 2,
        "description": "A Seraph station overrun by rogue AI. Scan drones, climb the tower, and stop Persys. Great entry-point dungeon for solo or duo players.",
        "activity_hash": 1923702891,
        "rewards": [
            {"hash": 4174431791, "clip_url": YT + "Hierarchy+of+Needs+destiny+2+exotic"},  # Hierarchy of Needs
        ],
        "tags": ["new-player", "solo", "exotic-hunter"],
    },
    {
        "id": "warlords-ruin",
        "name": "Warlord's Ruin",
        "category": "dungeon",
        "difficulty": 3,
        "description": "A harrowing gothic dungeon set in the EDZ's frozen mountains. Uncover the story of a corrupted Iron Lord and claim the unique exotic sidearm.",
        "activity_hash": 4088006058,
        "rewards": [
            {"hash": 3886719505, "clip_url": YT + "Buried+Bloodline+destiny+2+exotic"},  # Buried Bloodline
        ],
        "tags": ["solo", "exotic-hunter"],
    },
    {
        "id": "ghosts-of-the-deep",
        "name": "Ghosts of the Deep",
        "category": "dungeon",
        "difficulty": 3,
        "description": "Dive into the sunken Titan platforming hub and face ancient Hive lurking in the deep. The Navigator trace rifle is a top-tier support exotic.",
        "activity_hash": 313828469,
        "rewards": [
            {"hash": 1441805468, "clip_url": YT + "The+Navigator+destiny+2+exotic"},  # The Navigator
        ],
        "tags": ["solo", "exotic-hunter", "returning"],
    },
    {
        "id": "harbinger",
        "name": "Harbinger",
        "category": "exotic-mission",
        "difficulty": 2,
        "description": "A solo-friendly exotic mission set in the EDZ's Crow's Nest. Navigate through Taken corridors to reclaim Hawkmoon, the iconic hand cannon.",
        "activity_hash": 1738383283,
        "rewards": [
            {"hash": 3856705927, "clip_url": YT + "Hawkmoon+destiny+2+exotic"},  # Hawkmoon
        ],
        "tags": ["new-player", "solo", "exotic-hunter"],
    },
    {
        "id": "presage",
        "name": "Presage",
        "category": "exotic-mission",
        "difficulty": 2,
        "description": "An atmospheric horror-style exotic mission aboard a derelict Cabal ship. Unravel a mystery and earn Dead Man's Tale, a fan-favorite exotic scout rifle.",
        "activity_hash": 2124066889,
        "rewards": [
            {"hash": 2188764214, "clip_url": YT + "Dead+Man%27s+Tale+destiny+2+exotic"},  # Dead Man's Tale
        ],
        "tags": ["solo", "exotic-hunter"],
    },
    {
        "id": "operation-seraphs-shield",
        "name": "Operation: Seraph's Shield",
        "category": "exotic-mission",
        "difficulty": 2,
        "description": "Infiltrate a Seraph station and stop a rogue AI. Earn Revision Zero, a unique pulse rifle with a built-in alternate firing mode.",
        "activity_hash": 202306511,
        "rewards": [
            {"hash": 1473821207, "clip_url": YT + "Revision+Zero+destiny+2+exotic"},  # Revision Zero
        ],
        "tags": ["solo", "exotic-hunter", "returning"],
    },
]


# ── Models ─────────────────────────────────────────────────────────────────────


class PathfinderReward(BaseModel):
    name: str
    iconUrl: str | None
    acquired: bool
    clipUrl: str


class PathfinderEntry(BaseModel):
    id: str
    name: str
    category: str
    difficulty: int
    imageUrl: str | None
    description: str
    rewards: list[PathfinderReward]
    tags: list[str]


# ── Endpoint ───────────────────────────────────────────────────────────────────


@router.get("/pathfinder/guide", response_model=list[PathfinderEntry])
async def get_guide(
    membership_type: int,
    membership_id: str,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    all_reward_hashes = list({r["hash"] for entry in CONTENT_GUIDE for r in entry["rewards"]})
    all_activity_hashes = [entry["activity_hash"] for entry in CONTENT_GUIDE]

    collectibles_data, item_raws, activity_raws = await asyncio.gather(
        bungie_api.get_collectibles(membership_type, membership_id, access_token),
        manifest.get_items_batch(all_reward_hashes),
        asyncio.gather(*[manifest.get_activity(h) for h in all_activity_hashes]),
    )

    item_defns: dict[int, dict] = {}
    for raw in item_raws:
        defn = json.loads(raw)
        h = defn.get("hash")
        if h is not None:
            item_defns[h] = defn

    # Merge profile-level and all character-level collectibles.
    merged_collectibles: dict = {
        **collectibles_data.get("profileCollectibles", {}).get("data", {}).get("collectibles", {}),
    }
    for char_data in collectibles_data.get("characterCollectibles", {}).get("data", {}).values():
        for k, v in char_data.get("collectibles", {}).items():
            existing = merged_collectibles.get(k)
            if existing is None or (int(v.get("state", 1)) & 1) == 0:
                merged_collectibles[k] = v

    # Build a set of item hashes the player actually owns (vault + all character bags/equipment).
    # This is the fallback for exotics whose collectible state is unreliable
    # (seasonal missions like Presage/Seraph's Shield track ownership inconsistently).
    owned_item_hashes: set[int] = set()
    for item in collectibles_data.get("profileInventory", {}).get("data", {}).get("items", []):
        owned_item_hashes.add(item["itemHash"])
    for char_inv in collectibles_data.get("characterInventories", {}).get("data", {}).values():
        for item in char_inv.get("items", []):
            owned_item_hashes.add(item["itemHash"])
    for char_equip in collectibles_data.get("characterEquipment", {}).get("data", {}).values():
        for item in char_equip.get("items", []):
            owned_item_hashes.add(item["itemHash"])

    def is_acquired(col_hash: int, item_hash: int) -> bool:
        if item_hash in owned_item_hashes:
            return True
        state = int(merged_collectibles.get(str(col_hash), {}).get("state", 1))
        return (state & 1) == 0

    activity_image_map: dict[int, str | None] = {}
    for act_hash, raw in zip(all_activity_hashes, activity_raws):
        if raw:
            pgcr = json.loads(raw).get("pgcrImage")
            activity_image_map[act_hash] = f"https://www.bungie.net{pgcr}" if pgcr else None
        else:
            activity_image_map[act_hash] = None

    entries: list[PathfinderEntry] = []
    for entry in CONTENT_GUIDE:
        rewards: list[PathfinderReward] = []
        for reward_spec in entry["rewards"]:
            item_hash = reward_spec["hash"]
            defn = item_defns.get(item_hash, {})
            icon_path = defn.get("displayProperties", {}).get("icon", "")
            col_hash = defn.get("collectibleHash")
            acquired = is_acquired(col_hash, item_hash) if col_hash else item_hash in owned_item_hashes
            rewards.append(PathfinderReward(
                name=defn.get("displayProperties", {}).get("name", "Unknown Exotic"),
                iconUrl=f"https://www.bungie.net{icon_path}" if icon_path else None,
                acquired=acquired,
                clipUrl=reward_spec["clip_url"],
            ))

        entries.append(PathfinderEntry(
            id=entry["id"],
            name=entry["name"],
            category=entry["category"],
            difficulty=entry["difficulty"],
            imageUrl=activity_image_map.get(entry["activity_hash"]),
            description=entry["description"],
            rewards=rewards,
            tags=entry["tags"],
        ))

    entries.sort(key=lambda e: (all(r.acquired for r in e.rewards), e.difficulty))
    return entries
