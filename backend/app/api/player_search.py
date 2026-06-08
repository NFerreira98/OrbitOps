from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException, Query
from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["player"])
bungie_api = BungieAPI()
manifest = ManifestManager()

CLASS_NAMES = {0: "Titan", 1: "Hunter", 2: "Warlock"}

GEAR_SLOTS_BASIC: dict[int, str] = {
    1498876634: "Kinetic",   2465295065: "Energy",   953998645: "Power",
    3448274439: "Helmet",    3551918588: "Gauntlets", 14239492: "Chest",
    20886954:   "Legs",      1585787867: "Class Item",
    4023194814: "Ghost",     284967655:  "Ship",
}


@router.get("/player/search")
async def search_player(name: str = Query(...)):
    """Search by Bungie name (Name#1234) or prefix."""
    name = name.strip()
    if "#" in name:
        parts = name.rsplit("#", 1)
        display_name = parts[0]
        try:
            code = int(parts[1])
        except (ValueError, IndexError):
            raise HTTPException(400, "Format: Name#1234")
        player = await bungie_api.search_player_by_bungie_name(display_name, code)
        return {"results": [player] if player else []}
    results = await bungie_api.search_by_name_prefix(name)
    return {"results": results[:10]}


@router.get("/player/{membership_type}/{membership_id}/profile")
async def get_player_profile(membership_type: int, membership_id: str):
    """Public loadout for any Guardian — no auth required."""
    try:
        profile = await bungie_api.get_public_equipment(membership_type, membership_id)
    except Exception:
        raise HTTPException(404, "Profile not found or private")

    characters_data = profile.get("characters", {}).get("data", {})
    equipment_data  = profile.get("characterEquipment", {}).get("data", {})

    characters = []
    for char_id, char_info in characters_data.items():
        raw_items   = equipment_data.get(char_id, {}).get("items", [])
        item_hashes = [it["itemHash"] for it in raw_items if it.get("bucketHash") in GEAR_SLOTS_BASIC]

        defs_raw = await manifest.get_items_batch(item_hashes)
        def_map: dict[int, dict] = {}
        for raw in defs_raw:
            try:
                defn = json.loads(raw)
                h = defn.get("hash")
                if h:
                    def_map[h] = defn
            except Exception:
                pass

        gear = []
        for item in raw_items:
            bucket_hash = item.get("bucketHash")
            if bucket_hash not in GEAR_SLOTS_BASIC:
                continue
            defn = def_map.get(item["itemHash"])
            if not defn:
                continue
            dp = defn.get("displayProperties") or {}
            gear.append({
                "itemHash":            item["itemHash"],
                "slot":                GEAR_SLOTS_BASIC[bucket_hash],
                "name":                dp.get("name"),
                "icon":                dp.get("icon"),
                "itemTypeDisplayName": defn.get("itemTypeDisplayName"),
            })

        characters.append({
            "characterId": char_id,
            "className":   CLASS_NAMES.get(char_info.get("classType"), "Guardian"),
            "light":       char_info.get("light"),
            "emblemPath":  char_info.get("emblemPath"),
            "gear":        gear,
        })

    return {"characters": characters}
