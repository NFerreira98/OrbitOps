from __future__ import annotations
import asyncio
import json
import os
from pydantic import BaseModel
from fastapi import APIRouter, Header, HTTPException, Query
import anthropic

from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["vault"])
bungie_api = BungieAPI()
manifest = ManifestManager()

WEAPON_BUCKETS = {1498876634, 2465295065, 953998645}
ALL_GEAR_BUCKETS = WEAPON_BUCKETS | {3448274439, 3551918588, 14239492, 20886954, 1585787867, 284967655}

DAMAGE_TYPE: dict[int, str] = {
    0: "Prismatic", 2: "Arc", 3: "Solar", 4: "Void", 6: "Stasis", 7: "Strand",
}

SKIP_PLUG_TYPE_NAMES = {
    "Barrel", "Magazine", "Launcher Barrel", "Arrow", "Bowstring",
    "Grip", "Stock", "Guard", "Scope", "Tube", "Battery", "Blade", "Haft",
}

VAULT_EVALUATE_PROMPT = (
    "You are a Destiny 2 weapon expert helping a player clean their vault. "
    "They have multiple copies of the same weapon. Be direct and opinionated — no hedging.\n\n"
    "Respond in this exact format — nothing else:\n\n"
    "[1-2 sentences: what the weapon excels at and which perk combination matters most.]\n\n"
    "Keep: Copy #N — [one-line reason]\n"
    "Shard: Copy #N, Copy #N — [one-line reason]\n\n"
    "If exotics have fixed perks, base keep/shard on masterwork and power level only. "
    "No bullet points in the summary. No hedging."
)


# ── Models ─────────────────────────────────────────────────────────────────────


class VaultWeaponCopy(BaseModel):
    instanceId: str
    power: int
    perks: list[str]
    isMasterworked: bool


class VaultWeaponGroup(BaseModel):
    weaponHash: int
    name: str
    weaponType: str
    element: str
    isExotic: bool
    iconUrl: str | None
    copies: list[VaultWeaponCopy]


class EvaluateRequest(BaseModel):
    group: VaultWeaponGroup


class EquipRequest(BaseModel):
    instanceId: str
    itemHash: int
    membershipType: int
    membershipId: str
    characterId: str | None = None


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _is_meaningful_plug(defn: dict) -> bool:
    type_name = defn.get("itemTypeDisplayName", "")
    if type_name in SKIP_PLUG_TYPE_NAMES:
        return False
    plug_cat = defn.get("plug", {}).get("plugCategoryIdentifier", "")
    if any(skip in plug_cat for skip in ("masterwork", "shader", "tracker", "kill_tracker", "mod_socket", "empty")):
        return False
    name = defn.get("displayProperties", {}).get("name", "")
    if not name or name in ("Empty Socket", "Default Ornament", "Upgrade Masterwork"):
        return False
    return True


async def _fetch_vault_groups(
    membership_type: int,
    membership_id: str,
    access_token: str,
) -> list[VaultWeaponGroup]:
    profile = await bungie_api.get_vault_full(membership_type, membership_id, access_token)

    instances_data: dict = profile.get("itemComponents", {}).get("instances", {}).get("data", {})
    sockets_data: dict = profile.get("itemComponents", {}).get("sockets", {}).get("data", {})

    # Collect all instanced items from vault (102) and character bags (201).
    # Vault items always have bucketHash=138197802 — we filter to weapons AFTER
    # looking up definitions via inventory.bucketTypeHash.
    candidates: list[dict] = []
    seen: set[str] = set()

    vault_items = profile.get("profileInventory", {}).get("data", {}).get("items", [])
    for item in vault_items:
        h = item.get("itemHash")
        iid = str(item.get("itemInstanceId", ""))
        if h and iid and iid != "0" and iid not in seen:
            seen.add(iid)
            candidates.append({"instanceId": iid, "itemHash": h})

    char_inventories = profile.get("characterInventories", {}).get("data", {})
    for char_data in char_inventories.values():
        for item in char_data.get("items", []):
            h = item.get("itemHash")
            iid = str(item.get("itemInstanceId", ""))
            if h and iid and iid != "0" and item.get("bucketHash") in WEAPON_BUCKETS and iid not in seen:
                seen.add(iid)
                candidates.append({"instanceId": iid, "itemHash": h})

    if not candidates:
        return []

    # Batch-fetch all definitions; filter to weapons after
    unique_weapon_hashes = list({c["itemHash"] for c in candidates})
    all_plug_hashes: set[int] = set()
    for c in candidates:
        for s in sockets_data.get(c["instanceId"], {}).get("sockets", []):
            ph = s.get("plugHash")
            if ph:
                all_plug_hashes.add(ph)

    weapon_raws, plug_raws = await asyncio.gather(
        manifest.get_items_batch(unique_weapon_hashes),
        manifest.get_items_batch(list(all_plug_hashes)),
    )

    weapon_defns: dict[int, dict] = {}
    for raw in weapon_raws:
        defn = json.loads(raw)
        h = defn.get("hash")
        if h is not None:
            weapon_defns[h] = defn

    plug_defns: dict[int, dict] = {}
    for raw in plug_raws:
        defn = json.loads(raw)
        h = defn.get("hash")
        if h is not None:
            plug_defns[h] = defn

    # Filter candidates to weapons only (definition bucket must be a weapon slot)
    weapon_instances = [
        c for c in candidates
        if weapon_defns.get(c["itemHash"], {}).get("inventory", {}).get("bucketTypeHash") in WEAPON_BUCKETS
    ]

    # Group weapon copies by item hash
    groups_by_hash: dict[int, list[VaultWeaponCopy]] = {}

    for wi in weapon_instances:
        iid = wi["instanceId"]
        item_hash = wi["itemHash"]

        inst = instances_data.get(iid, {})
        power = inst.get("primaryStat", {}).get("value", 0)
        is_masterworked = inst.get("isMasterwork", False)

        sockets = sockets_data.get(iid, {}).get("sockets", [])
        perks: list[str] = []
        for s in sockets:
            ph = s.get("plugHash")
            if not ph:
                continue
            pdef = plug_defns.get(ph, {})
            if _is_meaningful_plug(pdef):
                name = pdef.get("displayProperties", {}).get("name", "")
                if name:
                    perks.append(name)

        copy = VaultWeaponCopy(
            instanceId=iid,
            power=power,
            perks=perks,
            isMasterworked=is_masterworked,
        )
        groups_by_hash.setdefault(item_hash, []).append(copy)

    # Build groups — only return weapons with 2+ copies
    groups: list[VaultWeaponGroup] = []
    for item_hash, copies in groups_by_hash.items():
        if len(copies) < 2:
            continue
        defn = weapon_defns.get(item_hash)
        if not defn:
            continue
        tier = defn.get("inventory", {}).get("tierType", 0)
        if tier < 5:  # skip below legendary
            continue
        damage = defn.get("defaultDamageType", -1)
        icon_path = defn.get("displayProperties", {}).get("icon", "")
        groups.append(VaultWeaponGroup(
            weaponHash=item_hash,
            name=defn.get("displayProperties", {}).get("name", "Unknown"),
            weaponType=defn.get("itemTypeDisplayName", "Weapon"),
            element=DAMAGE_TYPE.get(damage, "Kinetic"),
            isExotic=tier == 6,
            iconUrl=f"https://www.bungie.net{icon_path}" if icon_path else None,
            copies=sorted(copies, key=lambda c: c.power, reverse=True),
        ))

    groups.sort(key=lambda g: len(g.copies), reverse=True)
    return groups


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/vault/weapons", response_model=list[VaultWeaponGroup])
async def get_vault_weapons(
    membership_type: int,
    membership_id: str,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")
    try:
        return await _fetch_vault_groups(membership_type, membership_id, access_token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vault fetch failed: {e}")


@router.post("/vault/evaluate")
async def evaluate_weapon_group(
    body: EvaluateRequest,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    g = body.group
    lines = [f"Weapon: {g.name} ({g.weaponType}, {g.element}{'  [Exotic]' if g.isExotic else ''})"]
    for i, copy in enumerate(g.copies, 1):
        mw = " ★ Masterworked" if copy.isMasterworked else ""
        perks_str = " / ".join(copy.perks) if copy.perks else "No perks detected"
        lines.append(f"Copy #{i} — {copy.power} power{mw}: {perks_str}")

    user_message = "\n".join(lines)

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=VAULT_EVALUATE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return {"recommendation": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evaluation failed: {e}")


@router.post("/vault/equip")
async def equip_vault_item(
    body: EquipRequest,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    # Resolve character ID — use primary (most recently played) if not provided
    char_id = body.characterId
    if not char_id:
        profile = await bungie_api.get_profile(body.membershipType, body.membershipId, access_token)
        chars = profile.get("characters", {}).get("data", {})
        if not chars:
            raise HTTPException(status_code=404, detail="No characters found")
        char_id = max(chars, key=lambda cid: chars[cid].get("dateLastPlayed", ""))

    # Transfer from vault to character inventory, then equip
    try:
        await bungie_api.transfer_item(
            item_reference_hash=body.itemHash,
            instance_id=body.instanceId,
            character_id=char_id,
            membership_type=body.membershipType,
            access_token=access_token,
        )
    except Exception:
        pass  # item may already be on the character — proceed to equip

    try:
        await bungie_api.equip_item(
            instance_id=body.instanceId,
            character_id=char_id,
            membership_type=body.membershipType,
            access_token=access_token,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Equip failed: {e}")

    return {"success": True, "characterId": char_id}


# ── Gear slot alternatives ─────────────────────────────────────────────────────


class SlotItem(BaseModel):
    instanceId: str
    itemHash: int
    name: str
    power: int
    element: str
    itemType: str
    iconUrl: str | None
    isExotic: bool
    isMasterworked: bool
    perks: list[str]


@router.get("/gear/slot", response_model=list[SlotItem])
async def get_slot_alternatives(
    bucket_hash: int = Query(...),
    membership_type: int = Query(...),
    membership_id: str = Query(...),
    authorization: str = Header(...),
):
    """Return all unequipped items for a given gear slot (vault + character bags)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    try:
        profile = await bungie_api.get_vault_full(membership_type, membership_id, access_token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Profile fetch failed: {e}")

    instances_data: dict = profile.get("itemComponents", {}).get("instances", {}).get("data", {})
    sockets_data: dict = profile.get("itemComponents", {}).get("sockets", {}).get("data", {})

    # Collect items matching the requested bucket from vault + bags.
    # Vault items always have bucketHash=138197802; match them via definition later.
    candidates: list[dict] = []
    seen: set[str] = set()

    vault_items = profile.get("profileInventory", {}).get("data", {}).get("items", [])
    for item in vault_items:
        iid = str(item.get("itemInstanceId", ""))
        h = item.get("itemHash")
        if h and iid and iid not in seen:
            seen.add(iid)
            candidates.append({"instanceId": iid, "itemHash": h, "from_vault": True})

    char_inventories = profile.get("characterInventories", {}).get("data", {})
    for char_data in char_inventories.values():
        for item in char_data.get("items", []):
            if item.get("bucketHash") != bucket_hash:
                continue
            iid = str(item.get("itemInstanceId", ""))
            h = item.get("itemHash")
            if h and iid and iid not in seen:
                seen.add(iid)
                candidates.append({"instanceId": iid, "itemHash": h, "from_vault": False})

    if not candidates:
        return []

    # Batch-fetch item definitions and plug definitions in parallel
    unique_hashes = list({c["itemHash"] for c in candidates})
    all_plug_hashes: set[int] = set()
    for c in candidates:
        for s in sockets_data.get(c["instanceId"], {}).get("sockets", []):
            ph = s.get("plugHash")
            if ph:
                all_plug_hashes.add(ph)

    item_raws, plug_raws = await asyncio.gather(
        manifest.get_items_batch(unique_hashes),
        manifest.get_items_batch(list(all_plug_hashes)),
    )

    item_defns: dict[int, dict] = {}
    for raw in item_raws:
        defn = json.loads(raw)
        h = defn.get("hash")
        if h is not None:
            item_defns[h] = defn

    plug_defns: dict[int, dict] = {}
    for raw in plug_raws:
        defn = json.loads(raw)
        h = defn.get("hash")
        if h is not None:
            plug_defns[h] = defn

    results: list[SlotItem] = []
    for c in candidates:
        defn = item_defns.get(c["itemHash"])
        if not defn:
            continue
        # For vault items, check definition bucket matches the requested slot
        if c.get("from_vault") and defn.get("inventory", {}).get("bucketTypeHash") != bucket_hash:
            continue
        tier = defn.get("inventory", {}).get("tierType", 0)
        if tier < 5:
            continue

        iid = c["instanceId"]
        inst = instances_data.get(iid, {})
        power = inst.get("primaryStat", {}).get("value", 0)
        is_masterworked = inst.get("isMasterwork", False)
        damage = defn.get("defaultDamageType", -1)
        icon_path = defn.get("displayProperties", {}).get("icon", "")

        sockets = sockets_data.get(iid, {}).get("sockets", [])
        perks: list[str] = []
        for s in sockets:
            ph = s.get("plugHash")
            if not ph:
                continue
            pdef = plug_defns.get(ph, {})
            if _is_meaningful_plug(pdef):
                name = pdef.get("displayProperties", {}).get("name", "")
                if name:
                    perks.append(name)

        results.append(SlotItem(
            instanceId=iid,
            itemHash=c["itemHash"],
            name=defn.get("displayProperties", {}).get("name", "Unknown"),
            power=power,
            element=DAMAGE_TYPE.get(damage, "Kinetic"),
            itemType=defn.get("itemTypeDisplayName", ""),
            iconUrl=f"https://www.bungie.net{icon_path}" if icon_path else None,
            isExotic=tier == 6,
            isMasterworked=is_masterworked,
            perks=perks,
        ))

    results.sort(key=lambda x: x.power, reverse=True)
    return results
