from __future__ import annotations
import json
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["weekly"])
bungie_api = BungieAPI()
manifest = ManifestManager()


class MilestoneCard(BaseModel):
    hash: int
    name: str
    description: str
    icon: str | None
    milestoneType: int
    activityName: str | None
    endDate: str | None


@router.get("/weekly", response_model=dict)
async def get_weekly():
    try:
        milestones_raw = await bungie_api.get_public_milestones()
    except Exception:
        return {"milestones": [], "endDate": None}

    if not milestones_raw:
        return {"milestones": [], "endDate": None}

    milestone_hashes = [int(h) for h in milestones_raw.keys()]

    # Batch-fetch milestone definitions
    defs_raw = await manifest.get_milestones_batch(milestone_hashes)
    def_map: dict[int, dict] = {}
    for raw in defs_raw:
        try:
            defn = json.loads(raw)
            def_map[defn.get("hash", 0)] = defn
        except Exception:
            pass

    # Collect activity hashes to resolve names
    act_hashes: list[int] = []
    for milestone_data in milestones_raw.values():
        for act in (milestone_data.get("activities") or []):
            ah = act.get("activityHash")
            if ah:
                act_hashes.append(ah)

    act_defs_raw = await asyncio.gather(*[manifest.get_activity(ah) for ah in act_hashes])
    act_name_map: dict[int, str] = {}
    for ah, raw in zip(act_hashes, act_defs_raw):
        if raw:
            try:
                defn = json.loads(raw)
                name = (defn.get("displayProperties") or {}).get("name", "")
                if name and not defn.get("redacted"):
                    act_name_map[ah] = name
            except Exception:
                pass

    cards: list[dict] = []
    end_date: str | None = None

    for hash_str, milestone_data in milestones_raw.items():
        mhash = int(hash_str)
        defn  = def_map.get(mhash)
        if not defn:
            continue

        display = defn.get("displayProperties") or {}
        name    = display.get("name", "").strip()
        if not name:
            continue

        milestone_type = defn.get("milestoneType", 0)
        if milestone_type not in (3, 7):  # 3=Weekly, 7=Raid
            continue

        icon        = display.get("icon")
        description = display.get("description", "")

        activity_name: str | None = None
        for act in (milestone_data.get("activities") or []):
            ah = act.get("activityHash")
            if ah and ah in act_name_map:
                activity_name = act_name_map[ah]
                break

        if milestone_data.get("endDate") and not end_date:
            end_date = milestone_data["endDate"]

        cards.append({
            "hash":          mhash,
            "name":          name,
            "description":   description,
            "icon":          f"https://www.bungie.net{icon}" if icon else None,
            "milestoneType": milestone_type,
            "activityName":  activity_name,
            "endDate":       milestone_data.get("endDate"),
        })

    # Raids (type 7) first, then alphabetical
    cards.sort(key=lambda c: (0 if c["milestoneType"] == 7 else 1, c["name"]))

    return {"milestones": cards, "endDate": end_date}
