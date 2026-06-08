from __future__ import annotations
import json
import asyncio
from fastapi import APIRouter, Header, HTTPException, Query
from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["loadout"])
bungie_api = BungieAPI()
manifest = ManifestManager()

GEAR_SLOTS: dict[int, tuple[str, int]] = {
    1498876634: ("Kinetic",    0),
    2465295065: ("Energy",     1),
    953998645:  ("Power",      2),
    3448274439: ("Helmet",     3),
    3551918588: ("Gauntlets",  4),
    14239492:   ("Chest",      5),
    20886954:   ("Legs",       6),
    1585787867: ("Class Item", 7),
    4023194814: ("Ghost",      8),
    284967655:  ("Ship",       9),
}

SUBCLASS_BUCKET = 3284755031

# Plug categories to skip — cosmetics, trackers, empty slots
SKIP_PLUG_CATS = (
    "empty", "tracker", "shader", "ornament", "ghost_projection",
    "transmat", "emote", "finisher", "memento",
)

CLASS_NAMES = {0: "Titan", 1: "Hunter", 2: "Warlock"}


def _parse_perks(
    instance_id: str,
    sockets_data: dict,
    plug_def_map: dict[int, dict],
) -> list[dict]:
    item_sockets = sockets_data.get(instance_id, {}).get("sockets", [])
    perks: list[dict] = []
    for sock in item_sockets:
        plug_hash = sock.get("plugHash")
        if not plug_hash or not sock.get("isEnabled", True):
            continue
        defn = plug_def_map.get(plug_hash)
        if not defn:
            continue
        plug_info = defn.get("plug") or {}
        cat = (plug_info.get("plugCategoryIdentifier") or "").lower()
        if any(s in cat for s in SKIP_PLUG_CATS):
            continue
        dp = defn.get("displayProperties") or {}
        name = dp.get("name", "")
        desc = dp.get("description", "")
        icon = dp.get("icon")
        if not name or not desc or len(desc) < 15:
            continue
        perks.append({
            "name": name,
            "description": desc,
            "icon": f"https://www.bungie.net{icon}" if icon else None,
        })
        if len(perks) >= 6:
            break
    return perks


@router.get("/loadout")
async def get_loadout(
    membership_type: int = Query(...),
    membership_id: str = Query(...),
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    # 200=characters, 205=equipped, 300=instances (power), 305=sockets (perks)
    profile = await bungie_api.get_profile(
        membership_type, membership_id, access_token,
        components="200,205,300,305",
    )

    characters_data = profile.get("characters", {}).get("data", {})
    equipment_data  = profile.get("characterEquipment", {}).get("data", {})
    instances_data  = profile.get("itemComponents", {}).get("instances", {}).get("data", {})
    sockets_data    = profile.get("itemComponents", {}).get("sockets", {}).get("data", {})

    # Batch-fetch ALL plug definitions up front (one DB query for all characters)
    all_plug_hashes: set[int] = set()
    for char_id in equipment_data:
        for item in equipment_data.get(char_id, {}).get("items", []):
            iid = str(item.get("itemInstanceId", ""))
            for sock in sockets_data.get(iid, {}).get("sockets", []):
                ph = sock.get("plugHash")
                if ph:
                    all_plug_hashes.add(ph)

    plug_defs_raw = await manifest.get_items_batch(list(all_plug_hashes)) if all_plug_hashes else []
    plug_def_map: dict[int, dict] = {}
    for raw in plug_defs_raw:
        try:
            defn = json.loads(raw)
            h = defn.get("hash")
            if h:
                plug_def_map[h] = defn
        except Exception:
            pass

    characters = []
    for char_id, char_info in characters_data.items():
        raw_items = equipment_data.get(char_id, {}).get("items", [])
        subclass_name: str | None = None
        gear = []

        for item in raw_items:
            bucket_hash = item.get("bucketHash")
            item_hash   = item["itemHash"]
            instance_id = str(item.get("itemInstanceId", ""))

            if bucket_hash != SUBCLASS_BUCKET and bucket_hash not in GEAR_SLOTS:
                continue

            item_raw = await manifest.get_item(item_hash)
            if not item_raw:
                continue
            item_def = json.loads(item_raw)
            display  = item_def.get("displayProperties") or {}

            # Subclass detection
            if bucket_hash == SUBCLASS_BUCKET:
                subclass_name = item_def.get("itemTypeDisplayName") or display.get("name")
                continue

            slot_name, sort_order = GEAR_SLOTS[bucket_hash]
            inst  = instances_data.get(instance_id) or {}
            power = (inst.get("primaryStat") or {}).get("value", 0)

            lore_hash = item_def.get("loreHash")
            lore = None
            if lore_hash:
                lore_raw = await manifest.get_lore(lore_hash)
                if lore_raw:
                    lore_def     = json.loads(lore_raw)
                    lore_display = lore_def.get("displayProperties") or {}
                    lore = {
                        "title":       lore_display.get("name"),
                        "subtitle":    lore_def.get("subtitle"),
                        "description": lore_display.get("description"),
                    }

            perks = _parse_perks(instance_id, sockets_data, plug_def_map)

            gear.append({
                "instanceId":          instance_id,
                "itemHash":            item_hash,
                "bucketHash":          bucket_hash,
                "power":               power,
                "name":                display.get("name"),
                "icon":                display.get("icon"),
                "itemTypeDisplayName": item_def.get("itemTypeDisplayName"),
                "slot":                slot_name,
                "sortOrder":           sort_order,
                "lore":                lore,
                "perks":               perks,
            })

        gear.sort(key=lambda x: x["sortOrder"])

        characters.append({
            "characterId":          char_id,
            "className":            CLASS_NAMES.get(char_info.get("classType"), "Guardian"),
            "subclassName":         subclass_name,
            "light":                char_info.get("light"),
            "emblemPath":           char_info.get("emblemPath"),
            "emblemBackgroundPath": char_info.get("emblemBackgroundPath"),
            "gear":                 gear,
        })

    return {"characters": characters}
