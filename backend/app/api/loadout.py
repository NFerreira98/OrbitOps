import json
from fastapi import APIRouter, Header, HTTPException, Query
from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["loadout"])
bungie_api = BungieAPI()
manifest = ManifestManager()

# Slots we care about, in display order
GEAR_SLOTS: dict[int, tuple[str, int]] = {
    1498876634: ("Kinetic",    0),
    2465295065: ("Energy",     1),
    953998645:  ("Power",      2),
    3448274439: ("Helmet",     3),
    3551918588: ("Gauntlets",  4),
    14239492:   ("Chest",      5),
    20886954:   ("Legs",       6),
    1585787867: ("Class Item", 7),
    284967655:  ("Ghost",      8),
}

CLASS_NAMES = {0: "Titan", 1: "Hunter", 2: "Warlock"}


@router.get("/loadout")
async def get_loadout(
    membership_type: int = Query(...),
    membership_id: str = Query(...),
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    profile = await bungie_api.get_profile(membership_type, membership_id, access_token)

    characters_data = profile.get("characters", {}).get("data", {})
    equipment_data = profile.get("characterEquipment", {}).get("data", {})

    characters = []
    for char_id, char_info in characters_data.items():
        raw_items = equipment_data.get(char_id, {}).get("items", [])

        gear = []
        for item in raw_items:
            bucket_hash = item.get("bucketHash")
            if bucket_hash not in GEAR_SLOTS:
                continue

            slot_name, sort_order = GEAR_SLOTS[bucket_hash]
            item_hash = item["itemHash"]

            item_raw = await manifest.get_item(item_hash)
            if not item_raw:
                continue

            item_def = json.loads(item_raw)
            display = item_def.get("displayProperties", {})
            lore_hash = item_def.get("loreHash")

            lore = None
            if lore_hash:
                lore_raw = await manifest.get_lore(lore_hash)
                if lore_raw:
                    lore_def = json.loads(lore_raw)
                    lore_display = lore_def.get("displayProperties", {})
                    lore = {
                        "title": lore_display.get("name"),
                        "subtitle": lore_def.get("subtitle"),
                        "description": lore_display.get("description"),
                    }

            gear.append({
                "itemHash": item_hash,
                "name": display.get("name"),
                "icon": display.get("icon"),
                "itemTypeDisplayName": item_def.get("itemTypeDisplayName"),
                "slot": slot_name,
                "sortOrder": sort_order,
                "lore": lore,
            })

        gear.sort(key=lambda x: x["sortOrder"])

        characters.append({
            "characterId": char_id,
            "className": CLASS_NAMES.get(char_info.get("classType"), "Guardian"),
            "light": char_info.get("light"),
            "emblemPath": char_info.get("emblemPath"),
            "emblemBackgroundPath": char_info.get("emblemBackgroundPath"),
            "gear": gear,
        })

    return {"characters": characters}
