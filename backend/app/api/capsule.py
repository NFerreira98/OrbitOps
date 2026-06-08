from __future__ import annotations
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
import httpx
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response as HTTPResponse
from pydantic import BaseModel
import anthropic

from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["capsule"])
bungie_api = BungieAPI()
manifest = ManifestManager()

CLASS_NAMES = {0: "Titan", 1: "Hunter", 2: "Warlock"}
PLATFORM_NAMES = {1: "Xbox", 2: "PlayStation", 3: "Steam", 6: "Epic Games"}

ERA_ORDER = [
    "Red War",
    "Forsaken",
    "Shadowkeep",
    "Beyond Light",
    "Witch Queen",
    "Lightfall",
    "The Final Shape",
]

ERA_BY_SEASON: dict[int, str] = {
    **{s: "Red War" for s in range(1, 4)},
    **{s: "Forsaken" for s in range(4, 8)},
    **{s: "Shadowkeep" for s in range(8, 12)},
    **{s: "Beyond Light" for s in range(12, 16)},
    **{s: "Witch Queen" for s in range(16, 20)},
    **{s: "Lightfall" for s in range(20, 24)},
    **{s: "The Final Shape" for s in range(24, 30)},
}

SEASON_START_YEAR: dict[int, int] = {
    1: 2017, 2: 2017, 3: 2018, 4: 2018, 5: 2018, 6: 2019, 7: 2019,
    8: 2019, 9: 2019, 10: 2020, 11: 2020, 12: 2020, 13: 2021, 14: 2021,
    15: 2021, 16: 2022, 17: 2022, 18: 2022, 19: 2022, 20: 2023, 21: 2023,
    22: 2023, 23: 2023, 24: 2024, 25: 2024, 26: 2025,
}

@dataclass
class ArchetypeDef:
    name: str
    tier: int          # 1–5, higher = more prestigious / harder to unlock
    description: str
    unlock: Callable[..., bool]  # (raids, nf, pvp_matches, pvp_kd, pvp_wins, hours, titles) -> bool


# All archetypes ordered tier-descending. First match in _calculate_archetypes becomes the default.
ARCHETYPES: list[ArchetypeDef] = [
    # ── Tier 5: world-class ──────────────────────────────────────────────────
    ArchetypeDef(
        "Ghost of the Lighthouse", 5,
        "Marked by the Lighthouse and battle-hardened across 9 years. Elite in both PvP precision and endgame mastery.",
        lambda r, nf, pm, kd, pw, h, t: "Flawless" in t and kd >= 1.5 and pm >= 1000,
    ),
    ArchetypeDef(
        "The Ascendant", 5,
        "A Crucible force at the top of the competitive ladder. Few Guardians sustain this level of kill efficiency at volume.",
        lambda r, nf, pm, kd, pw, h, t: kd >= 1.5 and pw >= 3000,
    ),
    ArchetypeDef(
        "The Pantheon", 5,
        "Raider and Nightfall legend in one. A Guardian who committed to endgame at a level most never approach.",
        lambda r, nf, pm, kd, pw, h, t: r >= 200 and nf >= 500,
    ),
    # ── Tier 4: elite ────────────────────────────────────────────────────────
    ArchetypeDef(
        "Iron Crucible", 4,
        "Wins games and wins them decisively. A consistent PvP performer who paired volume with real efficiency.",
        lambda r, nf, pm, kd, pw, h, t: kd >= 1.5 and pw >= 2000,
    ),
    ArchetypeDef(
        "Endgame Devotee", 4,
        "Built for the hardest content. Raids and Grandmasters weren't optional — they were the entire point.",
        lambda r, nf, pm, kd, pw, h, t: r >= 50 and nf >= 200,
    ),
    ArchetypeDef(
        "Vault Conqueror", 4,
        "100+ raids cleared. The kind of player raid teams were built around.",
        lambda r, nf, pm, kd, pw, h, t: r >= 100,
    ),
    # ── Tier 3: veteran ──────────────────────────────────────────────────────
    ArchetypeDef(
        "Crucible Legend", 3,
        "A Crucible mainstay who backed their K/D with real volume. Not lucky — consistent.",
        lambda r, nf, pm, kd, pw, h, t: kd >= 2.0 and pm >= 500,
    ),
    ArchetypeDef(
        "Nightfall Master", 3,
        "The Nightfall grind demands precision, patience, and a team that doesn't quit. You had all three.",
        lambda r, nf, pm, kd, pw, h, t: nf >= 200,
    ),
    ArchetypeDef(
        "Raid Veteran", 3,
        "30+ raid clears means you were there for the hard ones — wipes, new mechanics, first clears.",
        lambda r, nf, pm, kd, pw, h, t: r >= 30,
    ),
    ArchetypeDef(
        "Iron Survivor", 3,
        "A thousand Crucible wins is a career. You built one.",
        lambda r, nf, pm, kd, pw, h, t: pw >= 1000,
    ),
    ArchetypeDef(
        "The Titled", 3,
        "Five or more titles earned. A completionist who finished what others abandoned.",
        lambda r, nf, pm, kd, pw, h, t: len(t) >= 5,
    ),
    # ── Tier 2: experienced ───────────────────────────────────────────────────
    ArchetypeDef(
        "The Dedicated", 2,
        "3,000+ hours is a second life. This was never just a game.",
        lambda r, nf, pm, kd, pw, h, t: h >= 3000,
    ),
    # ── Tier 1: base ─────────────────────────────────────────────────────────
    ArchetypeDef(
        "Veteran Guardian", 1,
        "A Guardian who put in the time and left a real record.",
        lambda r, nf, pm, kd, pw, h, t: h >= 1000,
    ),
    ArchetypeDef(
        "Guardian", 1,
        "A Guardian who answered the call.",
        lambda r, nf, pm, kd, pw, h, t: True,
    ),
]


# Curated prestige list: title -> (tier 1-5, flavour description)
# Tier 5 = extremely rare (<5%), tier 1 = uncommon. Tiers are estimates based
# on community data and Bungie's own rarity indicators.
PRESTIGE_TITLES: dict[str, tuple[int, str]] = {
    "Flawless":          (5, "Fewer than 5% of Guardians have ever gone Flawless. You did."),
    "Unbroken":          (5, "Forged through Crucible mastery alone. One of the rarest titles ever earned."),
    "Conqueror":         (5, "Reserved for those who conquered Grandmaster Nightfalls. The peak of PvE endgame."),
    "Pantheon":          (5, "Only those who conquered Pantheon — the hardest challenge ever created — carry this."),
    "Gilded Flawless":   (5, "Gilded Flawless. Worn by less than 1% of active Guardians."),
    "Gilded Conqueror":  (5, "Gilded Conqueror. The pinnacle of sustained PvE endgame achievement."),
    "Gilded Unbroken":   (5, "Gilded Unbroken. Among the rarest distinctions in all of Destiny."),
    "Rivensbane":        (4, "Earned through mastery of Last Wish. The first raid title. A mark that outlasted an era."),
    "Enlightened":       (4, "Awarded for full completion of Garden of Salvation. A dedicated team's highest proof."),
    "Descendant":        (4, "Forged in King's Fall. One of Destiny's most storied raid completions."),
    "Godslayer":         (4, "Awarded to those who completed every challenge in The Final Shape raid."),
    "Warlord":           (4, "Earned by conquering Salvation's Edge — the last great raid of the franchise."),
    "Fatebringer":       (4, "Vault of Glass in full. Named for the Vault's most legendary weapon."),
    "Disciple-Slayer":   (4, "For those who silenced The Witness's Disciple in Vow of the Disciple."),
    "Verity":            (4, "Earned by conquering Root of Nightmares at the edge of the solar system."),
    "Bonebreaker":       (4, "Awarded for full mastery of Crota's End."),
    "Cursebreaker":      (4, "For those who broke the Dreaming City's eternal curse in Forsaken."),
    "Deadeye":           (4, "Proven in Trials of Osiris with consistent Flawless performance."),
    "Reckoner":          (3, "Earned in the Reckoning — a title of Gambit mastery."),
    "Dredgen":           (3, "Carried by those who walked the Drifter's path to its end."),
    "Shadow":            (3, "For those who claimed the Gambit Prime title."),
    "Seraph":            (3, "For those who completed the full Season of the Seraph."),
    "Wayfarer":          (2, "Earned by exploring every destination and completing their full content."),
    "Chronicler":        (2, "For those who uncovered the full lore of the Forsaken era."),
    "Dauntless":         (2, "Awarded for consistent Nightfall mastery."),
}

GHOST_SYSTEM_PROMPT = (
    "You are writing three texts about a Destiny 2 Guardian's career. "
    "Format your response EXACTLY with these three section headers, each on their own line:\n\n"
    "[GHOST]\n"
    "Write a Ghost farewell letter. Voice: Light-forged AI companion, quiet and earned. "
    "Second person (you/your). 120–150 words. Reference their class, at least one era they were "
    "present for, specific stats, and any titles. End with something that acknowledges this is an "
    "earned ending. No markdown.\n\n"
    "[VERDICT]\n"
    "Write a What Defined You verdict. Voice: neutral analytical narrator, third person. "
    "50–70 words. Start with the guardian's name. State the single activity they most over-indexed "
    "on relative to the average player. Reference the exact numbers that prove it. "
    "Name their Destiny identity explicitly and declaratively — not 'seemed to enjoy' but 'was defined by'.\n\n"
    "[NUMBER]\n"
    "Pick the single most surprising or emotionally resonant stat from the data. "
    "Write exactly 2 sentences. First sentence states the raw number in context. "
    "Second sentence reframes its scale to make it personal and human. "
    "Example: 'You died 90,259 times. And got up 90,259 times.' No markdown."
)


# ── Models ─────────────────────────────────────────────────────────────────────


class CharacterSummary(BaseModel):
    characterId: str
    className: str
    light: int
    emblemPath: str | None
    emblemBackgroundPath: str | None
    isPrimary: bool


class SeasonEntry(BaseModel):
    hash: int
    name: str
    seasonNumber: int
    era: str
    description: str
    wasActive: bool


class RaidBookend(BaseModel):
    firstCharacterDate: str | None = None
    firstRaidDate: str | None = None
    lastRaidDate: str | None = None
    lastLoginDate: str | None = None
    raidCount: int = 0


class MonthlyPoint(BaseModel):
    period: str       # "YYYY-MM"
    era: str
    activities: int


class EraActivity(BaseModel):
    era: str
    activities: int
    relativeActivity: float   # 0.0–1.0 relative to the most active era
    monthsActive: int


class FireteamCompanion(BaseModel):
    displayName: str
    raidsTogetherSampled: int   # count from the sampled PGCRs, not full career


class PrestigeAchievement(BaseModel):
    name: str
    description: str
    tier: int         # 1–5


class ArchetypeEntry(BaseModel):
    name: str
    tier: int         # 1–5
    description: str


class CapsuleResponse(BaseModel):
    guardianName: str
    platform: str
    characters: list[CharacterSummary]
    hoursPlayed: float
    totalKills: int
    totalDeaths: int
    precisionKillPct: float
    raidsCleared: int
    nightfallsCleared: int
    strikesCleared: int
    pvpMatches: int
    pvpWins: int
    pvpKD: float
    titles: list[str]
    dateLastPlayed: str
    ghostNarrative: str
    seasons: list[SeasonEntry]
    archetype: str
    yearsActive: int
    firstSeason: str
    raidBookend: RaidBookend
    eraActivity: list[EraActivity]
    monthlyData: list[MonthlyPoint]
    prestigeAchievement: PrestigeAchievement | None = None
    verdict: str
    surpriseStat: str
    qualifiedArchetypes: list[ArchetypeEntry]
    fireteamCompanions: list[FireteamCompanion]


# ── Stat helpers ────────────────────────────────────────────────────────────────


def _val_any(merged: dict, mode_keys: list[str], stat: str) -> float:
    """Try multiple mode key variants and return the first non-zero value."""
    for key in mode_keys:
        v = merged.get(key, {}).get("allTime", {}).get(stat, {}).get("basic", {}).get("value", 0)
        if v:
            return float(v)
    return 0.0


def _period_to_era(period: str) -> str:
    """Map a YYYY-MM period string to a D2 expansion era."""
    ym = int(period[:4]) * 100 + int(period[5:7])
    if ym < 201809: return "Red War"
    if ym < 201910: return "Forsaken"
    if ym < 202011: return "Shadowkeep"
    if ym < 202202: return "Beyond Light"
    if ym < 202302: return "Witch Queen"
    if ym < 202406: return "Lightfall"
    return "The Final Shape"


def _calculate_archetypes(
    raids: int,
    nightfalls: int,
    pvp_matches: int,
    pvp_kd: float,
    pvp_wins: int,
    hours: float,
    titles: list[str],
) -> list[ArchetypeEntry]:
    """Return every archetype the player qualifies for, sorted by tier descending."""
    qualified: list[ArchetypeEntry] = []
    for defn in ARCHETYPES:
        try:
            if defn.unlock(raids, nightfalls, pvp_matches, pvp_kd, pvp_wins, hours, titles):
                qualified.append(ArchetypeEntry(name=defn.name, tier=defn.tier, description=defn.description))
        except Exception:
            continue
    qualified.sort(key=lambda a: -a.tier)
    return qualified


def _find_rarest_achievement(titles: list[str]) -> PrestigeAchievement | None:
    best: PrestigeAchievement | None = None
    for title in titles:
        info = PRESTIGE_TITLES.get(title)
        if info is None:
            continue
        tier, desc = info
        if best is None or tier > best.tier:
            best = PrestigeAchievement(name=title, description=desc, tier=tier)
    return best


def _compute_era_chart(monthly_data_list: list) -> tuple[list[MonthlyPoint], list[EraActivity]]:
    """Aggregate per-character monthly PvE stats into era-level activity totals."""
    monthly_totals: dict[str, int] = {}
    for data in monthly_data_list:
        if isinstance(data, Exception) or not isinstance(data, dict):
            continue
        for entry in data.get("allPvE", {}).get("monthly", []):
            period_raw = entry.get("period", "")
            if len(period_raw) < 7:
                continue
            period = period_raw[:7]
            acts = int(
                entry.get("values", {})
                .get("activitiesEntered", {})
                .get("basic", {})
                .get("value", 0)
            )
            if acts:
                monthly_totals[period] = monthly_totals.get(period, 0) + acts

    monthly_points: list[MonthlyPoint] = [
        MonthlyPoint(period=p, era=_period_to_era(p), activities=a)
        for p, a in sorted(monthly_totals.items())
    ]

    era_totals: dict[str, tuple[int, int]] = {}
    for mp in monthly_points:
        total, months = era_totals.get(mp.era, (0, 0))
        era_totals[mp.era] = (total + mp.activities, months + 1)

    if not era_totals:
        return monthly_points, []

    max_acts = max(v[0] for v in era_totals.values())
    era_activity = [
        EraActivity(
            era=era,
            activities=era_totals[era][0],
            relativeActivity=round(era_totals[era][0] / max(max_acts, 1), 3),
            monthsActive=era_totals[era][1],
        )
        for era in ERA_ORDER
        if era in era_totals
    ]
    return monthly_points, era_activity


# ── Async helpers ───────────────────────────────────────────────────────────────


async def _analyze_raid_history(
    char_ids: list[str],
    membership_type: int,
    membership_id: str,
    access_token: str,
) -> tuple[str | None, str | None, list[str]]:
    """Scan raid history for all characters.
    Returns (first_clear_date, last_clear_date, recent_instance_ids).
    Collects the 20 most recent completed instance IDs per character for PGCR sampling."""

    async def scan_char(char_id: str) -> tuple[str | None, str | None, list[str]]:
        oldest: str | None = None
        newest: str | None = None
        instances: list[str] = []
        for page in range(15):
            try:
                hist = await bungie_api.get_activity_history(
                    membership_type, membership_id, char_id, access_token,
                    mode=4, count=250, page=page,
                )
            except Exception:
                break
            activities = hist.get("activities") or []
            if not activities:
                break
            if page == 0:
                first = activities[0]
                print(
                    f"[raid-history] char {char_id[:6]}… page 0: {len(activities)} activities | "
                    f"first: period={first.get('period', '')[:10]}, "
                    f"completed={first.get('values', {}).get('completed', {}).get('basic', {}).get('value')}, "
                    f"instanceId={first.get('activityDetails', {}).get('instanceId')}"
                )
            for act in activities:
                completed = (
                    act.get("values", {})
                    .get("completed", {})
                    .get("basic", {})
                    .get("value", 0)
                )
                if float(completed) >= 0.5:
                    date = act.get("period", "")
                    if date:
                        if newest is None or date > newest:
                            newest = date
                        if oldest is None or date < oldest:
                            oldest = date
                    iid = str(act.get("activityDetails", {}).get("instanceId", ""))
                    if iid and iid != "0" and len(instances) < 20:
                        instances.append(iid)
            if len(activities) < 250:
                break
        return oldest, newest, instances

    results = await asyncio.gather(*[scan_char(cid) for cid in char_ids], return_exceptions=True)
    all_oldest = [r[0] for r in results if not isinstance(r, Exception) and r[0]]
    all_newest = [r[1] for r in results if not isinstance(r, Exception) and r[1]]

    seen: set[str] = set()
    unique_instances: list[str] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        for iid in r[2]:
            if iid not in seen:
                seen.add(iid)
                unique_instances.append(iid)

    print(f"[raid-history] collected {len(unique_instances)} unique instance IDs")
    return (
        min(all_oldest) if all_oldest else None,
        max(all_newest) if all_newest else None,
        unique_instances[:30],
    )


async def _find_fireteam_companions(
    instance_ids: list[str],
    own_membership_id: str,
) -> list[FireteamCompanion]:
    """Fetch PGCRs for sampled raid instances and rank fireteam companions by frequency."""
    if not instance_ids:
        print(f"[fireteam] no instance IDs collected — companions will be empty")
        return []

    print(f"[fireteam] fetching {len(instance_ids)} PGCRs for instances: {instance_ids[:3]}...")

    # Bungie rate-limits burst requests; cap concurrency to avoid 429s
    semaphore = asyncio.Semaphore(5)

    async def fetch_pgcr(iid: str) -> dict:
        async with semaphore:
            return await bungie_api.get_pgcr(iid)

    pgcr_results = await asyncio.gather(
        *[fetch_pgcr(iid) for iid in instance_ids],
        return_exceptions=True,
    )

    errors = sum(1 for r in pgcr_results if isinstance(r, Exception))
    print(f"[fireteam] PGCR results: {len(pgcr_results) - errors} ok, {errors} errors")
    if errors:
        sample_err = next(r for r in pgcr_results if isinstance(r, Exception))
        print(f"[fireteam] sample error: {sample_err}")

    counts: dict[str, tuple[str, int]] = {}  # membershipId -> (displayName, appearances)
    for result in pgcr_results:
        if isinstance(result, Exception) or not isinstance(result, dict):
            continue
        for entry in result.get("entries", []):
            user_info = entry.get("player", {}).get("destinyUserInfo", {})
            mid = str(user_info.get("membershipId", ""))
            if not mid or mid == own_membership_id:
                continue
            global_name = user_info.get("bungieGlobalDisplayName", "")
            code = user_info.get("bungieGlobalDisplayNameCode")
            if global_name:
                name = f"{global_name}#{code:04d}" if code else global_name
            else:
                name = user_info.get("displayName") or "Unknown Guardian"
            prev_name, prev_count = counts.get(mid, (name, 0))
            counts[mid] = (prev_name, prev_count + 1)

    print(f"[fireteam] found {len(counts)} unique companions")
    companions = sorted(
        [FireteamCompanion(displayName=n, raidsTogetherSampled=c) for _, (n, c) in counts.items()],
        key=lambda x: -x.raidsTogetherSampled,
    )
    return companions[:5]


async def _lookup_titles(title_hashes: set[int]) -> list[str]:
    titles: list[str] = []
    for th in title_hashes:
        record_raw = await manifest.get_record(th)
        if not record_raw:
            continue
        try:
            record_def = json.loads(record_raw)
            title = (
                record_def.get("titleInfo", {}).get("titlesByGender", {}).get("Male")
                or record_def.get("displayProperties", {}).get("name")
            )
            if title:
                titles.append(title)
        except Exception:
            continue
    return titles


async def _build_season_timeline(
    season_hashes: list[int],
    versions_owned: int,
) -> list[SeasonEntry]:
    season_raw_list = await manifest.get_all_season_definitions()
    active_set = set(season_hashes)

    # versionsOwned bitmask → season numbers the player was active for.
    # seasonHashes is unreliable for pre-BeyondLight seasons; bitmask is the primary signal.
    VERSION_SEASON_MAP: list[tuple[int, list[int]]] = [
        (1,    [1]),
        (2,    [2]),
        (4,    [3]),
        (8,    [4]),
        (16,   [5, 6, 7]),
        (32,   [8, 9, 10, 11]),
        (64,   [12, 13, 14, 15]),
        (256,  [16, 17, 18, 19]),
        (512,  [20, 21, 22, 23]),
        (1024, [24, 25, 26, 27]),
    ]
    version_active: set[int] = set()
    for bit, seasons in VERSION_SEASON_MAP:
        if versions_owned & bit:
            version_active.update(seasons)

    entries: list[SeasonEntry] = []
    for raw in season_raw_list:
        try:
            defn = json.loads(raw)
            season_num = defn.get("seasonNumber", 0)
            if season_num < 1:
                continue
            s_hash = defn.get("hash", 0)
            name = defn.get("displayProperties", {}).get("name") or f"Season {season_num}"
            description = defn.get("displayProperties", {}).get("description") or ""
            era = ERA_BY_SEASON.get(season_num, "The Final Shape")
            was_active = s_hash in active_set or season_num in version_active
            entries.append(SeasonEntry(
                hash=s_hash,
                name=name,
                seasonNumber=season_num,
                era=era,
                description=description[:400],
                wasActive=was_active,
            ))
        except Exception:
            continue

    entries.sort(key=lambda e: e.seasonNumber)
    return entries


def _parse_section(text: str, header: str, all_headers: list[str]) -> str:
    if header not in text:
        return ""
    start = text.index(header) + len(header)
    remaining = text[start:]
    end = len(remaining)
    for h in all_headers:
        if h != header and h in remaining:
            end = min(end, remaining.index(h))
    return remaining[:end].strip()


async def _generate_ghost_verdict_number(stats_context: str) -> tuple[str, str, str]:
    """Returns (ghost_narrative, verdict, surprise_stat)."""
    headers = ["[GHOST]", "[VERDICT]", "[NUMBER]"]
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=GHOST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": stats_context}],
        )
        text = response.content[0].text
        return (
            _parse_section(text, "[GHOST]", headers),
            _parse_section(text, "[VERDICT]", headers),
            _parse_section(text, "[NUMBER]", headers),
        )
    except Exception:
        return "Your record speaks for itself, Guardian.", "", ""


# ── Image proxy ─────────────────────────────────────────────────────────────────


@router.get("/proxy-image")
async def proxy_image(url: str = Query(...)):
    """Proxy bungie.net static assets so html2canvas sees them as same-origin."""
    if not url.startswith("https://www.bungie.net/"):
        raise HTTPException(status_code=400, detail="Only bungie.net URLs allowed")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=10.0)
            res.raise_for_status()
        return HTTPResponse(
            content=res.content,
            media_type=res.headers.get("content-type", "image/png"),
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch image")


# ── Endpoint ────────────────────────────────────────────────────────────────────


@router.get("/capsule", response_model=CapsuleResponse)
async def get_capsule(
    membership_type: int = Query(...),
    membership_id: str = Query(...),
    guardian_name: str = Query(default="Guardian"),
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    # Wave 1: account-level aggregate stats + profile metadata
    stats_data, profile_data = await asyncio.gather(
        bungie_api.get_historical_stats(membership_type, membership_id, access_token),
        bungie_api.get_profile_summary(membership_type, membership_id, access_token),
    )

    # Account-level endpoint only exposes allPvE / allPvP aggregates
    merged = stats_data.get("mergedAllCharacters", {}).get("results", {})
    pve_kills = _val_any(merged, ["allPvE", "7"], "kills")
    pvp_kills = _val_any(merged, ["allPvP", "5"], "kills")
    pve_precision = _val_any(merged, ["allPvE", "7"], "precisionKills")
    total_kills = int(pve_kills + pvp_kills)
    total_deaths = int(
        _val_any(merged, ["allPvE", "7"], "deaths")
        + _val_any(merged, ["allPvP", "5"], "deaths")
    )
    precision_pct = (pve_precision / max(pve_kills, 1)) * 100
    pve_seconds = _val_any(merged, ["allPvE", "7"], "secondsPlayed")
    pvp_seconds = _val_any(merged, ["allPvP", "5"], "secondsPlayed")
    hours_played = round((pve_seconds + pvp_seconds) / 3600, 1)
    pvp_matches = int(_val_any(merged, ["allPvP", "5"], "activitiesEntered"))
    pvp_wins = int(_val_any(merged, ["allPvP", "5"], "activitiesWon"))
    pvp_kd = round(_val_any(merged, ["allPvP", "5"], "killsDeathsRatio"), 2)

    # Profile metadata
    chars_raw = profile_data.get("characters", {}).get("data", {})
    profile_meta = profile_data.get("profile", {}).get("data", {})
    date_last_played = profile_meta.get("dateLastPlayed", "")
    season_hashes: list[int] = profile_meta.get("seasonHashes", [])
    versions_owned: int = profile_meta.get("versionsOwned", 0)

    primary_id = max(
        chars_raw,
        key=lambda cid: chars_raw[cid].get("dateLastPlayed", ""),
        default=None,
    )

    characters: list[CharacterSummary] = []
    title_hashes: set[int] = set()
    for char_id, char in chars_raw.items():
        title_hash = char.get("titleRecordHash", 0)
        if title_hash:
            title_hashes.add(title_hash)
        characters.append(CharacterSummary(
            characterId=char_id,
            className=CLASS_NAMES.get(char.get("classType"), "Guardian"),
            light=char.get("light", 0),
            emblemPath=char.get("emblemPath"),
            emblemBackgroundPath=char.get("emblemBackgroundPath"),
            isPrimary=(char_id == primary_id),
        ))
    characters.sort(key=lambda c: (not c.isPrimary, -c.light))
    char_ids = list(chars_raw.keys())

    # Wave 2: all per-character API calls + manifest lookups run in parallel
    char_stats_list, monthly_data_list, bookend_dates, seasons, titles = await asyncio.gather(
        asyncio.gather(
            *[bungie_api.get_character_stats(membership_type, membership_id, cid, access_token)
              for cid in char_ids],
            return_exceptions=True,
        ),
        asyncio.gather(
            *[bungie_api.get_monthly_stats(membership_type, membership_id, cid, access_token)
              for cid in char_ids],
            return_exceptions=True,
        ),
        _analyze_raid_history(char_ids, membership_type, membership_id, access_token),
        _build_season_timeline(season_hashes, versions_owned),
        _lookup_titles(title_hashes),
    )

    # Aggregate raid / nightfall / strike counts from character-level stats.
    # The character-level endpoint returns modes as top-level keys (no "results" wrapper).
    raids_cleared = 0
    strikes_cleared = 0
    nightfalls_cleared = 0
    for char_result in char_stats_list:
        if isinstance(char_result, Exception):
            continue
        r = char_result if isinstance(char_result, dict) else {}
        raids_cleared += int(_val_any(r, ["raid", "4"], "activitiesCleared"))
        strikes_cleared += int(_val_any(r, ["allStrikes", "18"], "activitiesCleared"))
        nightfalls_cleared += int(
            _val_any(r, ["nightfall", "16"], "activitiesCleared")
            + _val_any(r, ["heroicNightfall", "17"], "activitiesCleared")
            + _val_any(r, ["scoredNightfall", "46"], "activitiesCleared")
            + _val_any(r, ["scoredHeroicNightfall", "47"], "activitiesCleared")
        )

    # Era chart
    monthly_points, era_activity = _compute_era_chart(monthly_data_list)

    # Raid bookend timestamps
    first_raid_date, last_raid_date, raid_instance_ids = bookend_dates
    first_char_date: str | None = min(
        (c.get("dateCreated", "") for c in chars_raw.values() if c.get("dateCreated")),
        default=None,
    ) or None
    raid_bookend = RaidBookend(
        firstCharacterDate=first_char_date,
        firstRaidDate=first_raid_date,
        lastRaidDate=last_raid_date,
        lastLoginDate=date_last_played or None,
        raidCount=raids_cleared,
    )

    # Season analysis
    active_seasons = [s for s in seasons if s.wasActive]
    first_season = active_seasons[0].name if active_seasons else "the beginning"
    first_season_number = active_seasons[0].seasonNumber if active_seasons else 1
    start_year = SEASON_START_YEAR.get(first_season_number, 2017)
    years_active = datetime.now(timezone.utc).year - start_year

    qualified_archetypes = _calculate_archetypes(
        raids_cleared, nightfalls_cleared, pvp_matches, pvp_kd, pvp_wins, hours_played, titles,
    )
    archetype = qualified_archetypes[0].name if qualified_archetypes else "Guardian"
    prestige = _find_rarest_achievement(titles)
    primary_class = next((c.className for c in characters if c.isPrimary), "Guardian")
    active_era_names = list({s.era for s in active_seasons})

    stats_context = (
        f"Guardian record for {guardian_name}:\n"
        f"- Class: {primary_class}\n"
        f"- Archetype: {archetype}\n"
        f"- First season: {first_season} ({start_year})\n"
        f"- Years of service: {years_active}\n"
        f"- Eras active: {', '.join(active_era_names) if active_era_names else 'unknown'}\n"
        f"- Hours in the field: {hours_played:.0f}\n"
        f"- Total kills: {total_kills:,} ({precision_pct:.1f}% precision)\n"
        f"- Deaths: {total_deaths:,}\n"
        f"- Raids cleared: {raids_cleared}\n"
        f"- Nightfalls cleared: {nightfalls_cleared}\n"
        f"- Strikes cleared: {strikes_cleared}\n"
        f"- PvP record: {pvp_wins}W / {pvp_matches} matches, {pvp_kd:.2f} K/D\n"
        f"- Titles earned: {', '.join(titles) if titles else 'none'}\n"
        + (f"- Rarest title: {prestige.name} (tier {prestige.tier}/5)\n" if prestige else "")
    )
    # Wave 3: PGCR fetches + Claude run in parallel (both depend on Wave 2 results)
    (ghost_narrative, verdict, surprise_stat), fireteam_companions = await asyncio.gather(
        _generate_ghost_verdict_number(stats_context),
        _find_fireteam_companions(raid_instance_ids, membership_id),
    )

    return CapsuleResponse(
        guardianName=guardian_name,
        platform=PLATFORM_NAMES.get(membership_type, "Bungie.net"),
        characters=characters,
        hoursPlayed=hours_played,
        totalKills=total_kills,
        totalDeaths=total_deaths,
        precisionKillPct=round(precision_pct, 1),
        raidsCleared=raids_cleared,
        nightfallsCleared=nightfalls_cleared,
        strikesCleared=strikes_cleared,
        pvpMatches=pvp_matches,
        pvpWins=pvp_wins,
        pvpKD=pvp_kd,
        titles=titles,
        dateLastPlayed=date_last_played,
        ghostNarrative=ghost_narrative,
        seasons=seasons,
        archetype=archetype,
        yearsActive=years_active,
        firstSeason=first_season,
        raidBookend=raid_bookend,
        eraActivity=era_activity,
        monthlyData=monthly_points,
        prestigeAchievement=prestige,
        verdict=verdict,
        surpriseStat=surprise_stat,
        qualifiedArchetypes=qualified_archetypes,
        fireteamCompanions=fireteam_companions,
    )
