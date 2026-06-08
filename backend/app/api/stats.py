from __future__ import annotations
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["stats"])
bungie_api = BungieAPI()
manifest = ManifestManager()

CACHE_DIR = Path("data/stats_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_VERSION = 2

# ── Era mapping ───────────────────────────────────────────────────────────────

ERA_RANGES = [
    ("2017-09", "2018-08", "Red War"),
    ("2018-09", "2019-09", "Forsaken"),
    ("2019-10", "2020-10", "Shadowkeep"),
    ("2020-11", "2022-01", "Beyond Light"),
    ("2022-02", "2023-01", "Witch Queen"),
    ("2023-02", "2024-05", "Lightfall"),
    ("2024-06", "9999-12", "The Final Shape"),
]

def _month_to_era(month: str) -> str:
    for start, end, label in ERA_RANGES:
        if start <= month <= end:
            return label
    return "Pre-Release"

# ── Activity type → mode classification ───────────────────────────────────────

ACTIVITY_TYPE_MODE: dict[int, str] = {
    2043403989: "raid",
    608898761:  "dungeon",
    1227821118: "exotic-mission",
    # Strikes / Nightfalls
    2884569138: "strike", 2889152536: "strike", 3547475498: "strike",
    4110605575: "strike", 4164571395: "strike",
    272800122:  "strike", 575572995:  "strike",   # Nightfall
    # Crucible / PvP
    4088006058: "pvp", 1365291283: "pvp", 3252144427: "pvp", 3956381302: "pvp",
    3954711135: "pvp", 3956087078: "pvp", 2175955486: "pvp", 2394267841: "pvp",
    2371050408: "pvp", 2112637710: "pvp", 1957882444: "pvp",
    # Gambit
    2490937569: "gambit", 248695599: "gambit", 636666746: "gambit", 1418469392: "gambit",
}

# ── Weapon subtype → display name ─────────────────────────────────────────────

WEAPON_SUBTYPES: dict[int, str] = {
    6: "Auto Rifle", 7: "Bow", 9: "Hand Cannon", 10: "Rocket Launcher",
    11: "Fusion Rifle", 12: "Sniper Rifle", 13: "Pulse Rifle", 14: "Scout Rifle",
    17: "Submachine Gun", 18: "Sidearm", 23: "Grenade Launcher", 24: "Trace Rifle",
    25: "Machine Gun", 33: "Sword", 56: "Linear Fusion Rifle",
}

# ── Models ────────────────────────────────────────────────────────────────────

class TimelinePoint(BaseModel):
    month: str
    era: str
    pve: int
    pvp: int
    gambit: int

class ActivityEntry(BaseModel):
    activityHash: int
    name: str
    imageUrl: str | None
    completions: int
    fastestMs: int | None
    kills: int
    mode: str

class WeaponBucket(BaseModel):
    weaponType: str
    kills: int
    pct: float

class ModeBlock(BaseModel):
    mode: str
    label: str
    hoursPlayed: float
    kills: int
    activitiesEntered: int
    winRate: float | None

class ContextualStat(BaseModel):
    label: str
    raw: str
    frame: str

class PvpStats(BaseModel):
    kd: float
    kda: float
    efficiency: float
    combatRating: float
    totalKills: int
    totalDeaths: int
    totalAssists: int
    activitiesEntered: int
    activitiesWon: int
    precisionKills: int
    precisionPct: float
    bestSingleGameKills: int
    longestKillSpree: int
    longestLifeSecs: int
    winRate: float
    orbsDropped: int
    resurrectionsPerformed: int
    resurrectionsReceived: int

class AbilityStats(BaseModel):
    superKills: int
    grenadeKills: int
    meleeKills: int
    gunKills: int
    superPct: float
    grenadePct: float
    meleePct: float
    gunPct: float
    totalKills: int

class StatsDashboardResponse(BaseModel):
    cached: bool
    modes: list[ModeBlock]
    timeline: list[TimelinePoint]
    topActivities: list[ActivityEntry]
    weaponBuckets: list[WeaponBucket]
    contextualStats: list[ContextualStat]
    pvpStats: PvpStats | None = None
    abilityStats: AbilityStats | None = None

# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(membership_id: str) -> Path:
    return CACHE_DIR / f"{membership_id}.json"

def _read_cache(membership_id: str) -> dict | None:
    p = _cache_path(membership_id)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text())
        if payload.get("version", 1) < CACHE_VERSION:
            return None
        return payload
    except Exception:
        return None

def _write_cache(membership_id: str, data: dict) -> None:
    _cache_path(membership_id).write_text(json.dumps({
        "version": CACHE_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }))

# ── Helpers ───────────────────────────────────────────────────────────────────

def _val(stats: dict, key: str) -> float:
    """Safely extract a Bungie basic value — handles null at any nesting level."""
    container = (stats or {}).get(key) or {}
    basic = (container.get("basic") if isinstance(container, dict) else None) or {}
    return float((basic.get("value") if isinstance(basic, dict) else None) or 0.0)

def _merge_timeline(all_chars: list[dict]) -> list[TimelinePoint]:
    """Merge monthly stats from multiple characters into one timeline."""
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"pve": 0, "pvp": 0, "gambit": 0})
    mode_keys = [("allPvE", "pve"), ("allPvP", "pvp"), ("allPvECompetitive", "gambit")]

    for char_data in all_chars:
        for api_key, bucket_key in mode_keys:
            monthly = ((char_data.get(api_key) or {}).get("monthly") or {}).get("data") or []
            for point in monthly:
                month = point.get("period", "")[:7]
                if not month:
                    continue
                v = int(_val(point.get("values", {}), "activitiesEntered"))
                buckets[month][bucket_key] += v

    points = [
        TimelinePoint(month=m, era=_month_to_era(m), **v)
        for m, v in sorted(buckets.items())
    ]
    return points

def _merge_activities(all_chars: list[dict]) -> dict[int, dict]:
    merged: dict[int, dict] = {}
    for char_data in all_chars:
        for act in char_data.get("activities", []):
            h = act.get("activityHash")
            if not h:
                continue
            vals = act.get("values", {})
            completions = int(_val(vals, "activityCompletions"))
            kills = int(_val(vals, "activityKills"))
            fastest_raw = _val(vals, "fastestCompletionMsForActivity")
            fastest = int(fastest_raw) if fastest_raw > 0 else None
            if h not in merged:
                merged[h] = {"completions": 0, "kills": 0, "fastestMs": None}
            merged[h]["completions"] += completions
            merged[h]["kills"] += kills
            if fastest and (merged[h]["fastestMs"] is None or fastest < merged[h]["fastestMs"]):
                merged[h]["fastestMs"] = fastest
    return merged

def _merge_weapons(all_chars: list[dict]) -> dict[int, int]:
    """Returns {item_hash: kills} from uniqueWeapons across all characters."""
    totals: dict[int, int] = defaultdict(int)
    for char_data in all_chars:
        for mode_data in char_data.values():
            if not isinstance(mode_data, dict):
                continue
            all_time = mode_data.get("allTime") or {}
            for weapon in (all_time.get("uniqueWeapons") or []):
                ref_id = weapon.get("referenceId")
                kills = int(_val(weapon.get("values", {}), "uniqueWeaponKills"))
                if ref_id and kills > 0:
                    totals[ref_id] += kills
    return dict(totals)

def _mode_blocks(char_stats_list: list[dict]) -> list[ModeBlock]:
    totals: dict[str, dict] = {
        "pve": {"hours": 0.0, "kills": 0, "entered": 0, "won": 0},
        "pvp": {"hours": 0.0, "kills": 0, "entered": 0, "won": 0},
        "gambit": {"hours": 0.0, "kills": 0, "entered": 0, "won": 0},
    }
    mode_map = {
        "allPvE": "pve", "allPvP": "pvp", "allPvECompetitive": "gambit",
    }
    for char_data in char_stats_list:
        for api_key, bucket in mode_map.items():
            at = (char_data.get(api_key) or {}).get("allTime") or {}
            if not at:
                continue
            totals[bucket]["hours"] += _val(at, "secondsPlayed") / 3600
            totals[bucket]["kills"] += int(_val(at, "kills"))
            totals[bucket]["entered"] += int(_val(at, "activitiesEntered"))
            totals[bucket]["won"] += int(_val(at, "activitiesWon"))

    labels = {"pve": "PvE", "pvp": "Crucible", "gambit": "Gambit"}
    blocks = []
    for mode, t in totals.items():
        win_rate = (t["won"] / t["entered"] * 100) if t["entered"] > 0 else None
        blocks.append(ModeBlock(
            mode=mode,
            label=labels[mode],
            hoursPlayed=round(t["hours"], 1),
            kills=t["kills"],
            activitiesEntered=t["entered"],
            winRate=round(win_rate, 1) if win_rate is not None else None,
        ))
    return [b for b in blocks if b.activitiesEntered > 0]

def _contextual_stats(modes: list[ModeBlock]) -> list[ContextualStat]:
    total_hours = sum(m.hoursPlayed for m in modes)
    total_kills = sum(m.kills for m in modes)
    total_activities = sum(m.activitiesEntered for m in modes)

    days = total_hours / 24
    wembley = 90_000
    stadium_fills = total_kills / wembley

    top_mode = max(modes, key=lambda m: m.hoursPlayed) if modes else None
    top_pct = (top_mode.hoursPlayed / total_hours * 100) if top_mode and total_hours > 0 else 0

    stats = [
        ContextualStat(
            label="Time Played",
            raw=f"{int(total_hours):,} hours",
            frame=f"That's {days:.0f} days away from Earth — longer than it takes to get to Mars",
        ),
        ContextualStat(
            label="Enemies Slain",
            raw=f"{total_kills:,} kills",
            frame=f"You've filled Wembley Stadium {stadium_fills:.0f}x over with the fallen",
        ),
        ContextualStat(
            label="Activities",
            raw=f"{total_activities:,} completed",
            frame=f"Averaging {total_activities / max(total_hours, 1):.1f} activities per hour of play",
        ),
    ]
    if top_mode:
        stats.append(ContextualStat(
            label="Primary Passion",
            raw=f"{int(top_mode.hoursPlayed):,} hours in {top_mode.label}",
            frame=f"{top_pct:.0f}% of your Guardian life was spent in {top_mode.label}",
        ))
    return stats

def _pvp_stats(char_stats_list: list[dict]) -> PvpStats | None:
    totals: dict[str, int | float] = {
        "kills": 0, "deaths": 0, "assists": 0,
        "entered": 0, "won": 0,
        "precision": 0, "orbs": 0,
        "res_given": 0, "res_received": 0,
        "cr_sum": 0.0, "cr_weight": 0,
    }
    maximums = {"best_game": 0, "spree": 0, "life": 0}

    for char_data in char_stats_list:
        at = (char_data.get("allPvP") or {}).get("allTime") or {}
        if not at:
            continue
        entered = int(_val(at, "activitiesEntered"))
        totals["kills"]      += int(_val(at, "kills"))
        totals["deaths"]     += int(_val(at, "deaths"))
        totals["assists"]    += int(_val(at, "assists"))
        totals["entered"]    += entered
        totals["won"]        += int(_val(at, "activitiesWon"))
        totals["precision"]  += int(_val(at, "precisionKills"))
        totals["orbs"]       += int(_val(at, "orbsDropped"))
        totals["res_given"]  += int(_val(at, "resurrectionsPerformed"))
        totals["res_received"] += int(_val(at, "resurrectionsReceived"))
        if entered > 0:
            totals["cr_sum"]    += _val(at, "combatRating") * entered
            totals["cr_weight"] += entered
        maximums["best_game"] = max(maximums["best_game"], int(_val(at, "bestSingleGameKills")))
        maximums["spree"]     = max(maximums["spree"],     int(_val(at, "longestKillSpree")))
        maximums["life"]      = max(maximums["life"],      int(_val(at, "longestSingleLife")))

    entered = int(totals["entered"])
    if entered == 0:
        return None

    deaths = max(int(totals["deaths"]), 1)
    kills  = int(totals["kills"])
    assists = int(totals["assists"])
    cr = round(float(totals["cr_sum"]) / max(int(totals["cr_weight"]), 1), 1)

    return PvpStats(
        kd=round(kills / deaths, 2),
        kda=round((kills + assists) / deaths, 2),
        efficiency=round((kills + assists) / deaths, 2),
        combatRating=cr,
        totalKills=kills,
        totalDeaths=int(totals["deaths"]),
        totalAssists=assists,
        activitiesEntered=entered,
        activitiesWon=int(totals["won"]),
        precisionKills=int(totals["precision"]),
        precisionPct=round(int(totals["precision"]) / max(kills, 1) * 100, 1),
        bestSingleGameKills=maximums["best_game"],
        longestKillSpree=maximums["spree"],
        longestLifeSecs=maximums["life"],
        winRate=round(int(totals["won"]) / entered * 100, 1),
        orbsDropped=int(totals["orbs"]),
        resurrectionsPerformed=int(totals["res_given"]),
        resurrectionsReceived=int(totals["res_received"]),
    )

def _ability_stats(char_stats_list: list[dict]) -> AbilityStats | None:
    totals = {"super": 0, "grenade": 0, "melee": 0, "total": 0}

    for char_data in char_stats_list:
        for mode_key in ("allPvE", "allPvP", "allPvECompetitive"):
            at = (char_data.get(mode_key) or {}).get("allTime") or {}
            if not at:
                continue
            totals["super"]   += int(_val(at, "weaponKillsSuper"))
            totals["grenade"] += int(_val(at, "weaponKillsGrenade"))
            totals["melee"]   += int(_val(at, "weaponKillsMelee"))
            totals["total"]   += int(_val(at, "kills"))

    if totals["total"] == 0:
        return None

    ability = totals["super"] + totals["grenade"] + totals["melee"]
    gun_kills = max(totals["total"] - ability, 0)
    total = max(totals["total"], 1)

    return AbilityStats(
        superKills=totals["super"],
        grenadeKills=totals["grenade"],
        meleeKills=totals["melee"],
        gunKills=gun_kills,
        superPct=round(totals["super"]   / total * 100, 1),
        grenadePct=round(totals["grenade"] / total * 100, 1),
        meleePct=round(totals["melee"]   / total * 100, 1),
        gunPct=round(gun_kills / total * 100, 1),
        totalKills=totals["total"],
    )

# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/stats/dashboard", response_model=StatsDashboardResponse)
async def get_dashboard(
    membership_type: int,
    membership_id: str,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    cached = _read_cache(membership_id)
    if cached:
        return StatsDashboardResponse(**{**cached["data"], "cached": True})

    profile = await bungie_api.get_profile(membership_type, membership_id, access_token, components="200")
    characters: dict = profile.get("characters", {}).get("data", {})
    char_ids = list(characters.keys())
    if not char_ids:
        raise HTTPException(status_code=404, detail="No characters found")

    sem = asyncio.Semaphore(5)

    async def guarded(coro):
        async with sem:
            try:
                return await coro
            except Exception:
                return {}

    timeline_results, agg_results, weapon_results, mode_results = await asyncio.gather(
        asyncio.gather(*[
            guarded(bungie_api.get_monthly_stats_modes(membership_type, membership_id, cid, access_token))
            for cid in char_ids
        ]),
        asyncio.gather(*[
            guarded(bungie_api.get_aggregate_activity_stats(membership_type, membership_id, cid, access_token))
            for cid in char_ids
        ]),
        asyncio.gather(*[
            guarded(bungie_api.get_character_weapons_stats(membership_type, membership_id, cid, access_token))
            for cid in char_ids
        ]),
        asyncio.gather(*[
            guarded(bungie_api.get_lifetime_mode_stats(membership_type, membership_id, cid, access_token))
            for cid in char_ids
        ]),
    )

    # ── Timeline ──────────────────────────────────────────────────────────────
    timeline = _merge_timeline(list(timeline_results))

    # ── Modes ─────────────────────────────────────────────────────────────────
    modes = _mode_blocks(list(mode_results))

    # ── Activities ────────────────────────────────────────────────────────────
    raw_activities = _merge_activities(list(agg_results))
    top_hashes = sorted(raw_activities, key=lambda h: raw_activities[h]["completions"], reverse=True)[:40]

    act_defs_raw = await asyncio.gather(*[
        guarded(manifest.get_activity(h)) for h in top_hashes
    ])

    top_activities: list[ActivityEntry] = []
    for act_hash, raw in zip(top_hashes, act_defs_raw):
        if not raw:
            continue
        try:
            defn = json.loads(raw)
        except Exception:
            continue
        name = defn.get("displayProperties", {}).get("name", "")
        if not name or defn.get("redacted"):
            continue
        pgcr = defn.get("pgcrImage", "")
        image_url = f"https://www.bungie.net{pgcr}" if pgcr else None
        type_hash = defn.get("activityTypeHash", 0)
        mode = ACTIVITY_TYPE_MODE.get(type_hash, "misc")
        data = raw_activities[act_hash]
        top_activities.append(ActivityEntry(
            activityHash=act_hash,
            name=name,
            imageUrl=image_url,
            completions=data["completions"],
            fastestMs=data["fastestMs"],
            kills=data["kills"],
            mode=mode,
        ))

    top_activities = top_activities[:30]

    # ── Weapons ───────────────────────────────────────────────────────────────
    weapon_kills = _merge_weapons(list(weapon_results))
    top_weapon_hashes = sorted(weapon_kills, key=lambda h: weapon_kills[h], reverse=True)[:60]
    weapon_defs_raw = await manifest.get_items_batch(top_weapon_hashes) if top_weapon_hashes else []

    subtype_totals: dict[str, int] = defaultdict(int)
    for raw in weapon_defs_raw:
        try:
            defn = json.loads(raw)
        except Exception:
            continue
        subtype = defn.get("itemSubType", 0)
        label = WEAPON_SUBTYPES.get(subtype)
        if not label:
            continue
        h = defn.get("hash")
        if h and h in weapon_kills:
            subtype_totals[label] += weapon_kills[h]

    total_weapon_kills = sum(subtype_totals.values()) or 1
    weapon_buckets = sorted(
        [
            WeaponBucket(
                weaponType=wt,
                kills=k,
                pct=round(k / total_weapon_kills * 100, 1),
            )
            for wt, k in subtype_totals.items()
        ],
        key=lambda b: b.kills,
        reverse=True,
    )

    # ── Contextual stats ──────────────────────────────────────────────────────
    contextual_stats = _contextual_stats(modes)

    # ── PvP & Ability stats ────────────────────────────────────────────────────
    pvp_stats = _pvp_stats(list(mode_results))
    ability_stats = _ability_stats(list(mode_results))

    data = StatsDashboardResponse(
        cached=False,
        modes=modes,
        timeline=timeline,
        topActivities=top_activities,
        weaponBuckets=weapon_buckets,
        contextualStats=contextual_stats,
        pvpStats=pvp_stats,
        abilityStats=ability_stats,
    )

    _write_cache(membership_id, data.model_dump())
    return data
