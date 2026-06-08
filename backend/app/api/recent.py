from __future__ import annotations
import json
import asyncio
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["recent"])
bungie_api = BungieAPI()
manifest = ManifestManager()

MODE_DISPLAY: dict[int, str] = {
    2: "Story", 3: "Strike", 4: "Raid", 5: "Crucible",
    16: "Nightfall", 17: "Nightfall", 18: "Strike",
    46: "Nightfall", 47: "Nightfall", 68: "Dungeon",
    76: "Gambit", 80: "Gambit",
}


class RecentEntry(BaseModel):
    instanceId: str
    period: str
    activityName: str
    activityMode: int
    modeLabel: str
    completed: bool
    durationSecs: int
    kills: int
    deaths: int
    assists: int


def _v(values: dict, key: str) -> float:
    return ((values.get(key) or {}).get("basic") or {}).get("value") or 0.0


@router.get("/recent")
async def get_recent(
    membership_type: int,
    membership_id: str,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    profile = await bungie_api.get_profile(membership_type, membership_id, access_token, components="200")
    char_ids = list(profile.get("characters", {}).get("data", {}).keys())
    if not char_ids:
        return {"activities": []}

    histories = await asyncio.gather(*[
        bungie_api.get_activity_history(
            membership_type, membership_id, cid, access_token, mode=0, count=10
        )
        for cid in char_ids
    ])

    seen: set[str] = set()
    merged: list[dict] = []
    for history in histories:
        for act in (history.get("activities") or []):
            iid = (act.get("activityDetails") or {}).get("instanceId", "")
            if iid not in seen:
                seen.add(iid)
                merged.append(act)

    merged.sort(key=lambda a: a.get("period", ""), reverse=True)
    merged = merged[:20]

    ref_hashes = [(a.get("activityDetails") or {}).get("referenceId", 0) for a in merged]
    act_defs = await asyncio.gather(*[manifest.get_activity(h) for h in ref_hashes])

    entries: list[RecentEntry] = []
    for act, act_def_raw in zip(merged, act_defs):
        details = act.get("activityDetails") or {}
        values  = act.get("values") or {}

        activity_name = "Unknown Activity"
        if act_def_raw:
            try:
                defn = json.loads(act_def_raw)
                if not defn.get("redacted"):
                    activity_name = (defn.get("displayProperties") or {}).get("name", "Unknown Activity")
            except Exception:
                pass

        mode = details.get("mode", 0)
        entries.append(RecentEntry(
            instanceId=details.get("instanceId", ""),
            period=act.get("period", ""),
            activityName=activity_name,
            activityMode=mode,
            modeLabel=MODE_DISPLAY.get(mode, "Activity"),
            completed=bool(_v(values, "completed")),
            durationSecs=int(_v(values, "activityDurationSeconds")),
            kills=int(_v(values, "kills")),
            deaths=int(_v(values, "deaths")),
            assists=int(_v(values, "assists")),
        ))

    return {"activities": entries}
