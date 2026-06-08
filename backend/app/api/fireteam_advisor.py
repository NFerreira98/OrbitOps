from __future__ import annotations
import asyncio
import json
import os
from pydantic import BaseModel
from fastapi import APIRouter, Header, HTTPException, Query
import anthropic

from app.bungie.api import BungieAPI
from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["fireteam"])
bungie_api = BungieAPI()
manifest = ManifestManager()

# ── Manifest slot constants ───────────────────────────────────────────────────

SUBCLASS_BUCKET = 3284755031
WEAPON_BUCKETS  = {1498876634, 2465295065, 953998645}
ARMOR_BUCKETS   = {3448274439, 3551918588, 14239492, 20886954, 1585787867}

DAMAGE_TYPE: dict[int, str] = {
    0: "Prismatic",
    2: "Arc",
    3: "Solar",
    4: "Void",
    6: "Stasis",
    7: "Strand",
}

CLASS_NAMES: dict[int, str] = {0: "Titan", 1: "Hunter", 2: "Warlock"}

ALL_ELEMENTS = {"Solar", "Arc", "Void", "Stasis", "Strand"}

ELEMENT_COLORS: dict[str, str] = {
    "Solar":     "Solar (fire damage — Sunbreaker, Gunslinger, Dawnblade)",
    "Arc":       "Arc (lightning — Striker, Arcstrider, Stormcaller)",
    "Void":      "Void (shadow — Sentinel, Nightstalker, Voidwalker)",
    "Stasis":    "Stasis (ice — Behemoth, Revenant, Shadebinder)",
    "Strand":    "Strand (tangle — Berserker, Threadrunner, Broodweaver)",
    "Prismatic": "Prismatic (multi-element — combines Light and Dark abilities)",
}

# ── Activity database ─────────────────────────────────────────────────────────

ACTIVITIES: dict[str, dict] = {
    "garden-of-salvation": {
        "name": "Garden of Salvation",
        "type": "raid",
        "activityHash": 2659723068,
        "videoUrl": "https://www.youtube.com/results?search_query=Garden+of+Salvation+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Embrace",
                "weaponTypes": ["Auto Rifle", "Pulse Rifle", "Grenade Launcher"],
                "elements": ["Void", "Arc"],
                "exotics": ["Divinity"],
                "tip": "Long taken corridors. Void shields on major enemies. Divinity locks down the Hydra.",
                "steps": [
                    "Push through the corridors killing Taken adds — no DPS boss phase here.",
                    "Void shields are common; bring Void weapons or Divinity.",
                    "Kill the Hydra at the end of each section to advance.",
                ],
                "teams": [],
            },
            {
                "name": "The Consecrated Mind",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Solar"],
                "exotics": ["Divinity", "Gjallarhorn"],
                "tip": "Boss teleports. DPS during tether window — LFRs and rockets shine here.",
                "steps": [
                    "Split 3 left / 3 right — each lane has a Cyclops to kill.",
                    "Once your Cyclops is dead, stand on the tether plate and call 'ready'.",
                    "Both teams must tether simultaneously — call it over voice before stepping.",
                    "All 6 stack on the boss during the tether DPS window — LFRs and rockets.",
                    "Kill the Keeper of Petals (Servitor) after DPS to drop the boss's shield.",
                ],
                "teams": [
                    {"label": "Left Team (3p)", "role": "Kill left Cyclops → stand on tether plate → call ready"},
                    {"label": "Right Team (3p)", "role": "Kill right Cyclops → stand on tether plate → call ready"},
                ],
            },
            {
                "name": "The Sanctified Mind",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher", "Sniper Rifle"],
                "elements": ["Void", "Solar"],
                "exotics": ["Divinity", "Gjallarhorn", "Whisper of the Worm"],
                "tip": "Boss stays at extreme range. Swords CANNOT reach. LFRs and rockets only for DPS.",
                "steps": [
                    "Split 3 left / 3 right — each side has a Vex gate to enter.",
                    "Inside the gate, kill adds to collect Geometric Tally nodes.",
                    "Exit and deposit nodes at the center plate — do both sides simultaneously.",
                    "Boss becomes vulnerable — ALL switch to LFRs or rockets. Swords don't reach.",
                    "Repeat node collection until the boss is dead.",
                ],
                "teams": [
                    {"label": "Left Gate (3p)", "role": "Enter left Vex gate → collect nodes → deposit at center"},
                    {"label": "Right Gate (3p)", "role": "Enter right Vex gate → collect nodes → deposit at center"},
                ],
            },
        ],
    },
    "last-wish": {
        "name": "Last Wish",
        "type": "raid",
        "activityHash": 2122313384,
        "videoUrl": "https://www.youtube.com/results?search_query=Last+Wish+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Kalli",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle"],
                "elements": ["Solar", "Void"],
                "exotics": ["Gjallarhorn"],
                "tip": "Plate mechanic then brief DPS window. Boss teleports — keep rockets ready.",
                "steps": [
                    "Six plates are on the floor — each player watches a zone.",
                    "When plates glow, stand on yours immediately; all active plates held = Kalli bound.",
                    "Burst DPS during the vulnerability window — she stays in place briefly.",
                    "Kalli teleports and summons adds — clear adds fast and reset plate positions.",
                ],
                "teams": [],
            },
            {
                "name": "Shuro Chi",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Solar", "Arc"],
                "exotics": ["Gjallarhorn", "Xenophage"],
                "tip": "Running encounter — stay in DPS bubble (Well of Radiance). Rockets are ideal.",
                "steps": [
                    "Chase Shuro Chi across three bridge platforms — she retreats at each HP threshold.",
                    "Two players stand on the bind plates (one each side) to hold her still.",
                    "Kill Taken Psions IMMEDIATELY — each one that reaches her counts toward a team wipe.",
                    "DPS her during the bound window — Well of Radiance + rockets.",
                    "Watch for clock timers in your HUD; shoot them instantly or the whole team dies.",
                ],
                "teams": [
                    {"label": "Bind Team (2p, 1 each side)", "role": "Stand on the two plates to bind Shuro Chi for the DPS window"},
                    {"label": "Psion Killers + DPS (4p)", "role": "Immediately kill any Taken Psions that spawn, then burst DPS on Shuro Chi"},
                ],
            },
            {
                "name": "Morgeth",
                "weaponTypes": ["Rocket Launcher", "Sword", "Machine Gun"],
                "elements": ["Arc", "Solar"],
                "exotics": ["Gjallarhorn"],
                "tip": "Boss is stationary and close — swords work if brave. Standard rocket DPS.",
                "steps": [
                    "Kill adds around the arena to spawn Taken Strength orbs — pick up orbs carefully.",
                    "If you reach 2 Strength stacks you become Taken — another player must shoot you free.",
                    "Kill the two Eyes of Riven to open the DPS window.",
                    "Burst Morgeth — he's close and stationary so swords and rockets both work.",
                ],
                "teams": [],
            },
            {
                "name": "Riven",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Solar"],
                "exotics": ["Gjallarhorn", "Wish-Ender"],
                "tip": "Shoot the glowing eye/heart in her throat. Phase 1 is vertical — LFRs reach. Final room allows sword finisher.",
                "steps": [
                    "Split 3 left / 3 right — each team enters their side's maze of rooms.",
                    "Shoot Riven's correct glowing eye in each room — coordinate over voice.",
                    "After clearing all eyes, teleport to the central arena and shoot her glowing throat.",
                    "Run into her mouth before she closes it to escape instant death.",
                    "Final Queenswalk: one player uses the Sword of Riven to stab her exposed heart.",
                ],
                "teams": [
                    {"label": "Left Team (3p)", "role": "Enter left maze rooms → shoot correct eyes → call locations over voice"},
                    {"label": "Right Team (3p)", "role": "Enter right maze rooms → shoot correct eyes → call locations over voice"},
                ],
            },
        ],
    },
    "vault-of-glass": {
        "name": "Vault of Glass",
        "type": "raid",
        "activityHash": 3881495763,
        "videoUrl": "https://www.youtube.com/results?search_query=Vault+of+Glass+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Templar",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Solar"],
                "exotics": ["Fatebringer", "Gjallarhorn"],
                "tip": "Don't push Templar off the platform. Oracle cleanse first — DPS after relic slam.",
                "steps": [
                    "One player picks up the Relic from the center of the arena.",
                    "Oracles spawn in sequence — call locations and shoot them before they fully appear.",
                    "Relic holder uses the Relic's special attack (super button) to cleanse Marked teammates.",
                    "Relic holder slams the Relic on the Templar — this opens the DPS window.",
                    "Do NOT push the Templar off the platform (it voids the secret chest).",
                ],
                "teams": [
                    {"label": "Relic Holder (1p)", "role": "Pick up Relic → cleanse marked teammates → slam Relic on Templar to start DPS"},
                    {"label": "Team (5p)", "role": "Call and shoot Oracles as they spawn → burst DPS on Templar during the relic slam window"},
                ],
            },
            {
                "name": "Gatekeepers",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Arc", "Solar"],
                "exotics": ["Xenophage"],
                "tip": "Split fireteam across portals. Kill conflux defenders simultaneously.",
                "steps": [
                    "Two Vex portals open: one on each side. Each portal needs one player inside.",
                    "Portal players kill the Gatekeeper Minotaur and return its Relic to the outside.",
                    "Outside players defend the Conflux in the middle — kill all Vex before they sacrifice themselves.",
                    "After both Gatekeepers are dead, a third portal opens for the final brief encounter.",
                ],
                "teams": [
                    {"label": "Left Portal (1p)", "role": "Enter left portal → kill Gatekeeper → bring Relic back to outside team"},
                    {"label": "Right Portal (1p)", "role": "Enter right portal → kill Gatekeeper → bring Relic back to outside team"},
                    {"label": "Conflux Defense (4p)", "role": "Kill every Vex before they reach and sacrifice on the Conflux — one sacrifice = wipe"},
                ],
            },
            {
                "name": "Atheon",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher", "Hand Cannon"],
                "elements": ["Void", "Arc", "Solar"],
                "exotics": ["Fatebringer", "Gjallarhorn"],
                "tip": "Time's Vengeance buff after oracle clear — massive DPS window. Crit damage scales hard.",
                "steps": [
                    "Atheon randomly teleports 3 players into a time portal (Venus or Mars).",
                    "Teleported players kill Oracles in sequence, then escape through the portal exit.",
                    "Surviving the portal gives Time's Vengeance — a ~30s massive damage buff.",
                    "All 6 dump maximum DPS on Atheon while Time's Vengeance is active.",
                    "Outside players must kill Supplicant Vex (the exploding ones) or they detonate the team.",
                ],
                "teams": [
                    {"label": "Portaled players (3p, random)", "role": "Kill Oracles in order → escape portal → apply Time's Vengeance DPS on Atheon"},
                    {"label": "Outside players (3p, random)", "role": "Kill Supplicant Vex before they explode → burst DPS when Time's Vengeance is active"},
                ],
            },
        ],
    },
    "kings-fall": {
        "name": "King's Fall",
        "type": "raid",
        "activityHash": 1374392663,
        "videoUrl": "https://www.youtube.com/results?search_query=Kings+Fall+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Warpriest",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle"],
                "elements": ["Solar", "Arc"],
                "exotics": ["Gjallarhorn"],
                "tip": "Aura bearer stands in middle for DPS buff. Don't shoot without the aura active.",
                "steps": [
                    "Kill adds to find and pick up the Brand of the Initiate (glowing aura).",
                    "Aura holder stands inside the center circle to prevent the wipe timer from counting down.",
                    "Step on the three plates (left → middle → right) to brand the Warpriest.",
                    "DPS window opens when branded — do NOT shoot before the brand is active, damage is blocked.",
                    "Pass the Brand to a new player before it expires — communicate the handoff.",
                ],
                "teams": [
                    {"label": "Brand Holder (1p, rotates)", "role": "Hold the Brand → stand in center circle → pass it before it expires"},
                    {"label": "Plate Team + DPS (5p)", "role": "Stand plates in sequence to brand Warpriest → burst DPS during brand window"},
                ],
            },
            {
                "name": "Golgoroth",
                "weaponTypes": ["Linear Fusion Rifle", "Sniper Rifle", "Rocket Launcher"],
                "elements": ["Void", "Solar"],
                "exotics": ["Whisper of the Worm", "Gjallarhorn"],
                "tip": "Boss is suspended on ceiling. Short-range weapons miss. LFRs and snipers mandatory.",
                "steps": [
                    "Shoot one of the six ceiling chains to drop Golgoroth and start the encounter.",
                    "One player stands in front of Golgoroth to steal his Gaze (he turns to face you).",
                    "While the Gaze is held, the other 5 shoot his glowing belly for damage.",
                    "Pass the Gaze every ~15 seconds — the next player must step into his line of sight.",
                    "Boss hangs near the ceiling — swords and shotguns can't reach. LFRs and snipers only.",
                ],
                "teams": [
                    {"label": "Gaze Holder (1p, rotates)", "role": "Stand in Golgoroth's line of sight → hold Gaze for 15s → pass to next player"},
                    {"label": "DPS Team (5p)", "role": "Shoot Golgoroth's glowing belly while he's focused on the Gaze holder"},
                ],
            },
            {
                "name": "Daughters of Oryx",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Solar", "Arc"],
                "exotics": ["Gjallarhorn"],
                "tip": "Kill one daughter at a time during buff window. Team coordination critical.",
                "steps": [
                    "Two Daughters are on elevated platforms — only one is active at a time.",
                    "Kill adds to find the one carrying a Brand — that player becomes the Brand Stealer.",
                    "Brand Stealer runs the Brand to the active Daughter's plate to brand her.",
                    "DPS window opens on the branded Daughter — burst her down, then switch to the second.",
                    "Repeat the branding process for the second Daughter.",
                ],
                "teams": [
                    {"label": "Brand Stealer (1p, rotates)", "role": "Kill Brand-carrying add → pick up Brand → run to Daughter's plate to brand her"},
                    {"label": "DPS + Add Clear (5p)", "role": "Kill adds on platforms → burst the branded Daughter during the DPS window"},
                ],
            },
            {
                "name": "Oryx",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle", "Sword"],
                "elements": ["Void", "Solar", "Arc"],
                "exotics": ["Gjallarhorn"],
                "tip": "Stagger Oryx by bombing his chest. Swords work in the final deathsinger phase.",
                "steps": [
                    "Kill Taken Knights around the arena — each drops a Relic (bomb).",
                    "Three Relic carriers run to their plates around Oryx and slam the Relics to stagger him.",
                    "Oryx staggers and his heart glows — ALL players burst DPS on the exposed heart.",
                    "After DPS, run to the back wall — Oryx detonates and instantly kills anyone nearby.",
                    "Final phase: kill the Shade of Oryx and cleanse the Harrowed runes to finish.",
                ],
                "teams": [
                    {"label": "Relic Carriers (3p)", "role": "Grab Relic from slain Knight → run to designated plate → slam Relic to stagger Oryx"},
                    {"label": "Add Clear + DPS (3p)", "role": "Kill Taken adds → protect Relic carriers → burst DPS on Oryx's exposed heart"},
                ],
            },
        ],
    },
    "root-of-nightmares": {
        "name": "Root of Nightmares",
        "type": "raid",
        "activityHash": 2381413764,
        "videoUrl": "https://www.youtube.com/results?search_query=Root+of+Nightmares+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Cataclysm",
                "weaponTypes": ["Auto Rifle", "Grenade Launcher"],
                "elements": ["Arc", "Solar"],
                "exotics": [],
                "tip": "Traverse the arena killing Tormentors. No DPS phase — survivability matters.",
                "steps": [
                    "No boss DPS phase — this is traversal and add clearing.",
                    "Collect Light/Dark Transcendence orbs to build up your Transcendence buff.",
                    "Use Transcendence to open the glowing path nodes and advance forward.",
                    "Tormentors two-shot isolated players — stay as a group and use ranged weapons.",
                ],
                "teams": [],
            },
            {
                "name": "Scission",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle"],
                "elements": ["Strand", "Void"],
                "exotics": [],
                "tip": "Two-lane split mechanic. Coordinate Light/Dark side roles.",
                "steps": [
                    "Split Light team (left) and Dark team (right) at the start.",
                    "Each side stands on their colored plate and collects matching Transcendence nodes.",
                    "Both teams deposit their nodes at the center simultaneously.",
                    "Boss becomes vulnerable — all 6 DPS together with LFRs and rockets.",
                ],
                "teams": [
                    {"label": "Light Team (3p)", "role": "Stand on Light plate → collect Light nodes → deposit at center"},
                    {"label": "Dark Team (3p)", "role": "Stand on Dark plate → collect Dark nodes → deposit at center"},
                ],
            },
            {
                "name": "Macrocosm",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Solar", "Arc"],
                "exotics": [],
                "tip": "Planet-shooting mechanic. Fast movement required — prioritize survivability exotics.",
                "steps": [
                    "Shoot the planets around the arena with Strand to move them into the correct tubes.",
                    "Left team handles left planets, right team handles right — call when your side is done.",
                    "After planets inserted, boss becomes vulnerable — DPS window opens.",
                    "Tormentors spawn between phases — kill them before they close to melee range.",
                ],
                "teams": [
                    {"label": "Left Planets (3p)", "role": "Shoot and guide left-side planets into the correct Light/Dark tubes"},
                    {"label": "Right Planets (3p)", "role": "Shoot and guide right-side planets into the correct Light/Dark tubes"},
                ],
            },
            {
                "name": "Nezarec",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle", "Sword"],
                "elements": ["Strand", "Void"],
                "exotics": ["Divinity", "Gjallarhorn"],
                "tip": "Debuff with Void weapons (Weaken = huge DPS boost). Divinity locks the debuff in place.",
                "steps": [
                    "Kill adds to collect Resonance orbs — orbs come in Light and Dark types.",
                    "Deposit the correct orb type on Nezarec's body to put him to sleep.",
                    "Once asleep, his chest glows — ALL DPS immediately. Void Weaken debuff is critical here.",
                    "Divinity locks the Weaken debuff in place — use it for every phase if available.",
                    "Repeat 4-5 cycles — he wakes up after each DPS phase.",
                ],
                "teams": [
                    {"label": "Orb Runners (2-3p)", "role": "Collect Resonance orbs from slain adds → deposit on Nezarec to put him to sleep"},
                    {"label": "DPS Team (3-4p)", "role": "Apply Void Weaken (Tractor Cannon/Graviton) → burst DPS on his exposed chest"},
                ],
            },
        ],
    },
    "crotas-end": {
        "name": "Crota's End",
        "type": "raid",
        "activityHash": 4179289725,
        "videoUrl": "https://www.youtube.com/results?search_query=Crotas+End+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "The Abyss",
                "weaponTypes": ["Machine Gun", "Auto Rifle"],
                "elements": ["Arc", "Solar"],
                "exotics": [],
                "tip": "Survive the darkness — stay in lantern light. No DPS, pure survival.",
                "steps": [
                    "The arena is completely dark — standing in darkness drains your HP rapidly.",
                    "Run between glowing Lamps to stay alive.",
                    "Kill Knights roaming near Lamps before they extinguish them.",
                    "All 6 stick together — stragglers die fast when their lamp goes out.",
                ],
                "teams": [],
            },
            {
                "name": "The Bridge",
                "weaponTypes": ["Rocket Launcher", "Sniper Rifle"],
                "elements": ["Arc", "Void"],
                "exotics": [],
                "tip": "Two teams: one builds bridge, one defends. Coordinate the handoff precisely.",
                "steps": [
                    "One team starts near-side, one team starts far-side at the same time.",
                    "Near-side team grabs the Sword of Crota from a Knight to use against Swordbearers on the bridge.",
                    "Both teams fight across/defend the bridge simultaneously — call when you reach the far side.",
                    "After all 6 are across, kill the Knight at the end to proceed.",
                ],
                "teams": [
                    {"label": "Near Side (3p)", "role": "Grab Sword → cut Swordbearers blocking the bridge → fight across"},
                    {"label": "Far Side (3p)", "role": "Defend the bridge far-side from Hive adds until all 6 are across"},
                ],
            },
            {
                "name": "Ir Yut",
                "weaponTypes": ["Sniper Rifle", "Rocket Launcher"],
                "elements": ["Solar", "Void"],
                "exotics": [],
                "tip": "Kill adds first to open the Deathsinger's window. Then burst her fast.",
                "steps": [
                    "A countdown timer begins when you enter the chamber — Ir Yut wipes the team when it hits zero.",
                    "Kill all Hive adds (Wizards, Knights, Acolytes) in the room first.",
                    "Once adds are cleared, burst Ir Yut immediately — she has no phase mechanic, just raw DPS.",
                    "Snipers and rockets work well — she has high HP for a timed encounter.",
                ],
                "teams": [],
            },
            {
                "name": "Crota",
                "weaponTypes": ["Sword"],
                "elements": ["Solar", "Void"],
                "exotics": [],
                "tip": "SWORD ONLY for DPS — the Sword of Crota is the only weapon that works on his knees. One sword bearer at a time.",
                "steps": [
                    "Kill the Swordbearer Knight that walks alongside Crota — he drops the Sword of Crota.",
                    "One player picks up the Sword, gets behind Crota, and hits his knees with the melee attack.",
                    "Land 2-3 hits then back off before the Sword timer runs out — carrying it too long = death.",
                    "Repeat with a fresh Sword each time — only one sword carrier at a time.",
                    "The Chalice of Light must be held at all times — if dropped, Crota fully regenerates HP.",
                ],
                "teams": [
                    {"label": "Swordbearer (1p, rotates)", "role": "Kill Swordbearer Knight → pick up Sword → land 2-3 knee hits on Crota → retreat"},
                    {"label": "Chalice Holder (1p, rotates)", "role": "Hold the Chalice of Light at all times — pass it before it expires or Crota regens to full"},
                    {"label": "Support (4p)", "role": "Kill adds → shoot Crota's shield when he kneels → protect the Swordbearer"},
                ],
            },
        ],
    },
    "salvations-edge": {
        "name": "Salvation's Edge",
        "type": "raid",
        "activityHash": 1541433876,
        "videoUrl": "https://www.youtube.com/results?search_query=Salvations+Edge+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Substratum",
                "weaponTypes": ["Auto Rifle", "Grenade Launcher"],
                "elements": ["Strand", "Void"],
                "exotics": [],
                "tip": "First encounter — learning the Witness's core mechanic with nodes and shapes.",
                "steps": [
                    "Light team (left) and Dark team (right) each shoot nodes of their color on the arena walls.",
                    "Nodes must be shot in a specific sequence — a designated caller reads the order.",
                    "After completing the sequence, all 6 run to the cage and stand in it to deposit.",
                    "Repeat the node sequence until the encounter is complete.",
                ],
                "teams": [
                    {"label": "Light Team (3p)", "role": "Shoot Light nodes in the called sequence → run to cage to deposit"},
                    {"label": "Dark Team (3p)", "role": "Shoot Dark nodes in the called sequence → run to cage to deposit"},
                ],
            },
            {
                "name": "Repository",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Arc", "Solar"],
                "exotics": [],
                "tip": "Shape-passing mechanic requires crisp communication. Pre-assign roles.",
                "steps": [
                    "Left team and right team each handle their side's shape puzzle.",
                    "Shapes can only be passed across the gap — throw to teammates on the opposite platform.",
                    "Insert the correct shapes into their designated slots to open the DPS window.",
                    "All 6 DPS the boss with rockets and LFRs during the exposure window.",
                ],
                "teams": [
                    {"label": "Left Team (3p)", "role": "Handle left-side shapes → throw across gap when called → insert into slots"},
                    {"label": "Right Team (3p)", "role": "Handle right-side shapes → throw across gap when called → insert into slots"},
                ],
            },
            {
                "name": "Dissipation",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Strand", "Arc"],
                "exotics": [],
                "tip": "Most mechanically complex encounter — roles must be pre-assigned before loading in.",
                "steps": [
                    "Four platforms split into Light/Dark pairs — players must stand on the opposite type to tether.",
                    "Light players stand on Dark platforms, Dark players stand on Light platforms.",
                    "A runner collects the tether buffs and deposits them at the central node.",
                    "Pre-assign roles before loading in — this encounter punishes confusion instantly.",
                ],
                "teams": [
                    {"label": "Light Tethers (2p)", "role": "Stand on Dark platforms to generate Light tethers"},
                    {"label": "Dark Tethers (2p)", "role": "Stand on Light platforms to generate Dark tethers"},
                    {"label": "Runner (1p)", "role": "Collect tether buffs from all platforms → deposit at the central node"},
                    {"label": "Caller / Floater (1p)", "role": "Call node positions over voice → cover any missed tethers"},
                ],
            },
            {
                "name": "The Witness",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher", "Sword"],
                "elements": ["Strand", "Void", "Solar"],
                "exotics": ["Divinity", "Gjallarhorn"],
                "tip": "Final boss. Longest DPS window in any raid — burst and sustained damage both matter. Divinity critical.",
                "steps": [
                    "Split left / right — same node mechanic as the earlier encounters, scaled up.",
                    "Each side completes their node sequence and deposits at the Witness's weak point.",
                    "DPS window opens — Divinity + LFRs is the meta. Use every super and heavy you have.",
                    "The Witness resets after each phase — 4-5 cycles before he's dead.",
                    "Well of Radiance + Banner Shield stacked together maximizes DPS uptime.",
                ],
                "teams": [
                    {"label": "Left Team (3p)", "role": "Complete left-side node sequence → deposit at Witness weak point"},
                    {"label": "Right Team (3p)", "role": "Complete right-side node sequence → deposit at Witness weak point"},
                ],
            },
        ],
    },
    "ghosts-of-the-deep": {
        "name": "Ghosts of the Deep",
        "type": "dungeon",
        "activityHash": 313828469,
        "videoUrl": "https://www.youtube.com/results?search_query=Ghosts+of+the+Deep+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Ecthar, Sword of Oryx",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Void", "Solar"],
                "exotics": ["Gjallarhorn"],
                "tip": "Dunk orbs to debuff Ecthar. Stagger him three times during the DPS window.",
                "steps": [
                    "Kill Lightbearer Hive enemies — they drop the Lure of the Deep.",
                    "Lure carrier runs to one of three ritual circles and stands in it with 2+ others nearby.",
                    "Complete three rituals to fully debuff Ecthar — each ritual opens a brief DPS window.",
                    "After three rituals, Ecthar is staggers — burst him with rockets before he resets.",
                ],
                "teams": [
                    {"label": "Lure Carriers (2-3p)", "role": "Kill Lightbearers → pick up Lure → stand in ritual circle with allies to complete it"},
                    {"label": "Add Clear (3p)", "role": "Kill Hive adds → protect Lure carriers from being overwhelmed during rituals"},
                ],
            },
            {
                "name": "Simmumah ur-Nokru",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Arc"],
                "exotics": ["Whisper of the Worm", "Gjallarhorn"],
                "tip": "Final boss teleports between platforms. LFRs reach no matter where boss repositions.",
                "steps": [
                    "Same Lure ritual mechanic — complete three rituals to open the DPS phase.",
                    "Simmumah teleports between platforms — use LFRs and rockets to hit her anywhere.",
                    "After each DPS phase she revives like a Lucent Brood Witch — find and kill her Ghost fast.",
                    "If her Ghost escapes she fully revives — Ghost hunting is the critical role here.",
                ],
                "teams": [
                    {"label": "Lure Team (2-3p)", "role": "Complete three Lure rituals to open the boss DPS phase"},
                    {"label": "Ghost Hunters (1-2p)", "role": "Locate and kill the boss's Ghost immediately after each DPS phase to prevent full revival"},
                ],
            },
        ],
    },
    "warlords-ruin": {
        "name": "Warlord's Ruin",
        "type": "dungeon",
        "activityHash": 4088006058,
        "videoUrl": "https://www.youtube.com/results?search_query=Warlords+Ruin+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Rathil",
                "weaponTypes": ["Rocket Launcher", "Sniper Rifle"],
                "elements": ["Arc", "Solar"],
                "exotics": ["Gjallarhorn"],
                "tip": "Kill adds to reveal boss weak points. Damage during exposed window only.",
                "steps": [
                    "Kill Hive adds around the arena to charge the encounter.",
                    "Rathil's armor cracks when enough adds are killed — shoot the glowing weak points.",
                    "Three damage phases of increasing difficulty — finish him on the third or he enrages.",
                    "All 3 focus-fire the same weak point at the same time for maximum efficiency.",
                ],
                "teams": [],
            },
            {
                "name": "Hefnd's Vengeance",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Solar"],
                "exotics": ["Gjallarhorn", "Whisper of the Worm"],
                "tip": "Final boss — same kill-adds mechanic escalated. LFRs and rockets for DPS burst.",
                "steps": [
                    "Same kill-adds mechanic as Rathil, but with more enemies and tighter timing.",
                    "Hefnd moves between platforms — LFRs let you hit her regardless of position.",
                    "Kill adds between phases to find the next Lure drop for ritual resets.",
                    "Use supers and heavy ammo on every single DPS window — don't hold anything back.",
                ],
                "teams": [],
            },
        ],
    },
    "spire-of-the-watcher": {
        "name": "Spire of the Watcher",
        "type": "dungeon",
        "activityHash": 1923702891,
        "videoUrl": "https://www.youtube.com/results?search_query=Spire+of+the+Watcher+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Akelous",
                "weaponTypes": ["Machine Gun", "Rocket Launcher"],
                "elements": ["Arc", "Void"],
                "exotics": ["Thunderlord"],
                "tip": "Drone-scanning mechanic. Arc weapons deal bonus damage — lean into Arc loadout.",
                "steps": [
                    "Scan the drones flying around the arena — they flash a code in a specific sequence.",
                    "Four players each stand on one of four plates simultaneously to lock in the code.",
                    "Locking the correct code drops Akelous lower — all 3 DPS him during his exposed phase.",
                    "Arc weapons deal bonus damage throughout this dungeon — Thunderlord is best in slot.",
                ],
                "teams": [
                    {"label": "Plate Holders (all 3p at once)", "role": "Stand on correct plates simultaneously after reading the drone code sequence"},
                ],
            },
            {
                "name": "Persys, Primordial Ruin",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Arc", "Solar"],
                "exotics": ["Thunderlord", "Gjallarhorn"],
                "tip": "Shoot terminals to open DPS window. Arc surge is active — Arc weapons preferred.",
                "steps": [
                    "Kill Exploding Shanks and Servitors to collect Arc Charges.",
                    "Deposit Arc Charges into both terminals simultaneously to breach Persys's shield.",
                    "One player stands in the breach portal; two others shoot them to transfer energy.",
                    "Energy transferred → shoot Persys's glowing weak points. Arc surge makes Arc weapons essential.",
                ],
                "teams": [
                    {"label": "Charge Runners (2p)", "role": "Collect Arc Charges from Servitors → deposit in both terminals simultaneously"},
                    {"label": "Breach Team (1p in breach + others outside)", "role": "One stands in the breach portal; teammates shoot them to send energy to Persys's weak points"},
                ],
            },
        ],
    },
    "deep-stone-crypt": {
        "name": "Deep Stone Crypt",
        "type": "raid",
        "activityHash": 3976949817,
        "videoUrl": "https://www.youtube.com/results?search_query=Deep+Stone+Crypt+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Crypt Security",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Solar", "Arc"],
                "exotics": ["Gjallarhorn"],
                "tip": "Break fuses by standing in the correct augmented zones. Clear ads fast — the floor kills.",
                "steps": [
                    "One scanner reads which fuse needs breaking; two operators hold augments to break them.",
                    "Fuses have a time limit — swap augments quickly between scanner and operators.",
                    "Kill the Security Mind boss once all fuses are broken.",
                ],
                "teams": [
                    {"label": "Scanner", "role": "Read which fuse plate is active and call it out"},
                    {"label": "Operators (2)", "role": "Hold operator augment, stand on active fuse plate to destroy it"},
                ],
            },
            {
                "name": "Atraks-1, Fallen Exo",
                "weaponTypes": ["Linear Fusion Rifle", "Sniper Rifle"],
                "elements": ["Void", "Stasis"],
                "exotics": ["Whisper of the Worm", "Divinity"],
                "tip": "DPS the correct Atraks copy in space OR on the ground. Void/Stasis weapons chunk her shield.",
                "steps": [
                    "Half the fireteam portals into space, half stays on ground — each fights a copy of Atraks.",
                    "Scanner identifies which copies are the real ones; only the real ones take damage.",
                    "Replicants drop a Servitor orb — pass it to the other side before time runs out.",
                    "Final DPS window: both sides damage simultaneously.",
                ],
                "teams": [
                    {"label": "Space Team (3)", "role": "Enter portal, find scanner-marked copy, DPS, pass orb down"},
                    {"label": "Ground Team (3)", "role": "Fight ground-side copies, receive orbs from space, DPS simultaneously"},
                ],
            },
            {
                "name": "Taniks, Restricted",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle"],
                "elements": ["Solar", "Arc"],
                "exotics": ["Gjallarhorn"],
                "tip": "Taniks floats in zero-gravity. Shoot nuclear cores into the correct slam zones — fast.",
                "steps": [
                    "Taniks drops nuclear cores from his back when shot — grab them immediately.",
                    "Each core must be dunked in a specific zone before it explodes in your hands.",
                    "Do not stand near a core holder — the explosion chain-kills nearby players.",
                ],
                "teams": [
                    {"label": "Core Runners (3)", "role": "Pick up nuclear cores and sprint to the correct dunk zone"},
                    {"label": "DPS/Ads (3)", "role": "Shoot Taniks to drop cores; clear ads around dunk zones"},
                ],
            },
            {
                "name": "Taniks, the Abomination",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle"],
                "elements": ["Solar", "Arc"],
                "exotics": ["Eyes of Tomorrow", "Gjallarhorn"],
                "tip": "Dunk four nuclear cores simultaneously to begin DPS. Eyes of Tomorrow deals massive burst on this boss.",
                "steps": [
                    "Same core-running mechanic — but all four cores must be dunked at the same time.",
                    "Once all four dunk zones are activated, Taniks becomes vulnerable.",
                    "DPS window is short — Eyes of Tomorrow and Gjallarhorn are the best options.",
                    "Repeat 3× for final stand.",
                ],
                "teams": [
                    {"label": "Core Runners (4)", "role": "Each player grabs one core and dunks simultaneously on callout"},
                    {"label": "Support (2)", "role": "Clear ads, apply Well/Banner, call out correct dunk zones"},
                ],
            },
        ],
    },
    "vow-of-the-disciple": {
        "name": "Vow of the Disciple",
        "type": "raid",
        "activityHash": 1441982566,
        "videoUrl": "https://www.youtube.com/results?search_query=Vow+of+the+Disciple+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Acquisition",
                "weaponTypes": ["Machine Gun", "Rocket Launcher"],
                "elements": ["Void", "Strand"],
                "exotics": [],
                "tip": "Learn the symbol language used throughout the entire raid — you'll need it every encounter.",
                "steps": [
                    "Kill the Resonance Vessel to pick up a buff; the buff-holder sees a symbol on the pyramid.",
                    "Three symbols cycle — the one NOT shown is what you deposit at the obelisk.",
                    "Defend the obelisk while it charges. Repeat for all three pyramidion wings.",
                ],
                "teams": [
                    {"label": "Symbol Reader", "role": "Hold the Taken Essence, call out the symbol shown to you"},
                    {"label": "Defenders (rest)", "role": "Kill ads and Resonance Vessels; guard obelisks while charging"},
                ],
            },
            {
                "name": "Caretaker",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Arc"],
                "exotics": ["Divinity"],
                "tip": "Read symbols fast and deposit them before the Caretaker reaches the obelisk — or it's a wipe.",
                "steps": [
                    "Split into readers (inside) and DPS (outside on plates).",
                    "Readers match symbols on Caretaker's body to symbols on obelisks — call the correct one.",
                    "Depositing the right symbol staggers Caretaker and opens a DPS window.",
                    "Three stuns = DPS phase. Don't let Caretaker reach the obelisk.",
                ],
                "teams": [
                    {"label": "Symbol Readers (3)", "role": "Enter the main chamber, read Caretaker's symbols, call obelisk to deposit"},
                    {"label": "Plate Holders (3)", "role": "Stand on matching floor plates outside to keep doors open for readers"},
                ],
            },
            {
                "name": "Exhibition",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Void", "Stasis"],
                "exotics": [],
                "tip": "Guard the relics from Scorn as you carry them through the dark hallways. Don't drop them.",
                "steps": [
                    "Designate relic carriers — they cannot shoot but must protect their relic from being stolen.",
                    "Remaining players kill Scorn ads aggressively; Ravenous Scorn will try to steal relics.",
                    "Deposit all relics at the far altar before time runs out. Coordinate movement.",
                ],
                "teams": [
                    {"label": "Relic Carriers (3)", "role": "Carry relics forward; cannot shoot — call out when Scorn are stealing"},
                    {"label": "Escort (3)", "role": "Destroy all Scorn, especially Ravenous Scorn (relic thieves), aggressively"},
                ],
            },
            {
                "name": "Rhulk, Disciple of the Witness",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Strand"],
                "exotics": ["Collective Obligation", "Divinity"],
                "tip": "Collective Obligation is the raid exotic — only Rhulk drops it. Divinity makes debuffing trivial.",
                "steps": [
                    "Phase 1: Drain Rhulk's Leeching Force by reading and matching symbols.",
                    "Once Leeching Force hits zero, the Emanating Force DPS window opens.",
                    "Phase 2 (after first DPS): Rhulk gains more aggressive patterns — same loop but faster.",
                    "Final stand at ~20% HP: pure DPS race, use all supers.",
                ],
                "teams": [
                    {"label": "Symbol Readers (3)", "role": "Track Rhulk's Leeching Force symbols; call the matching altar"},
                    {"label": "DPS (3)", "role": "Burst Rhulk during Emanating Force window — LFRs and rockets required"},
                ],
            },
        ],
    },
    "desert-perpetual": {
        "name": "The Desert Perpetual",
        "type": "raid",
        "activityHash": 1044919065,
        "videoUrl": "https://www.youtube.com/results?search_query=Desert+Perpetual+raid+guide+destiny+2",
        "encounters": [
            {
                "name": "Encounter 1",
                "weaponTypes": ["Rocket Launcher", "Linear Fusion Rifle"],
                "elements": ["Void", "Solar"],
                "exotics": [],
                "tip": "Edge of Fate raid — coordinate callouts and follow the symbol/mechanic pattern.",
                "steps": [
                    "Learn the core mechanic introduced in this encounter — it repeats throughout the raid.",
                    "Assign roles before pulling and stick to them.",
                ],
                "teams": [],
            },
            {
                "name": "Encounter 2",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Void", "Arc"],
                "exotics": [],
                "tip": "Second mechanic layer adds complexity. Keep communication tight.",
                "steps": [
                    "Build on the first encounter's mechanic with an added layer.",
                    "Split roles cleanly — two players on mechanic, rest on DPS.",
                ],
                "teams": [],
            },
            {
                "name": "Final Boss",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Solar"],
                "exotics": ["Whirling Ovation"],
                "tip": "Whirling Ovation drops from this boss. Burst DPS during the damage window.",
                "steps": [
                    "Complete the final boss mechanic to open the DPS phase.",
                    "Use Linear Fusion Rifles or Rocket Launchers for maximum burst damage.",
                ],
                "teams": [],
            },
        ],
    },
    "shattered-throne": {
        "name": "Shattered Throne",
        "type": "dungeon",
        "activityHash": 2032534090,
        "videoUrl": "https://www.youtube.com/results?search_query=Shattered+Throne+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Vorgeth, the Boundless Hunger",
                "weaponTypes": ["Rocket Launcher", "Sniper Rifle"],
                "elements": ["Void", "Solar"],
                "exotics": ["Gjallarhorn"],
                "tip": "Kill Petitioner adds to collect Dissolution — deposit to remove Vorgeth's shield.",
                "steps": [
                    "Four Petitioner Wizards orbit the arena — kill them to collect their Dissolution buff.",
                    "Each Dissolution carry can be deposited into a statue pedestal to weaken Vorgeth's shield.",
                    "Once all four pedestals are charged, Vorgeth's shield drops — burst him with rockets.",
                    "He re-shields quickly — restart the cycle. Three DPS phases kills him.",
                ],
                "teams": [],
            },
            {
                "name": "Dul Incaru, the Eternal Return",
                "weaponTypes": ["Sniper Rifle", "Rocket Launcher"],
                "elements": ["Void"],
                "exotics": ["Whisper of the Worm"],
                "tip": "Kill Taken Knights to remove Dul Incaru's damage immunity before each DPS phase.",
                "steps": [
                    "Three Taken Knights spawn — all must die simultaneously to drop the boss's immunity.",
                    "Coordinate kills: each player focuses one knight and calls out before firing.",
                    "Once all three drop at the same time, Dul Incaru becomes damageable — heavy burst.",
                    "Void resistance and Void weapons are optimal throughout this encounter.",
                ],
                "teams": [
                    {"label": "Knight Killers (1 each)", "role": "Each player focuses one of three Taken Knights — call out and kill simultaneously on a countdown"},
                ],
            },
        ],
    },
    "pit-of-heresy": {
        "name": "Pit of Heresy",
        "type": "dungeon",
        "activityHash": 2582501063,
        "videoUrl": "https://www.youtube.com/results?search_query=Pit+of+Heresy+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Necropolis",
                "weaponTypes": ["Sword", "Rocket Launcher"],
                "elements": ["Solar", "Void"],
                "exotics": ["Lament"],
                "tip": "Three Hive symbols must be matched across the tower floors — communicate what you see.",
                "steps": [
                    "Three symbols appear on the outside of the tower — memorize them.",
                    "Each player descends a different shaft and finds the matching symbol inside.",
                    "Kill the Hive Knight behind the matching symbol to collect Hive Rune.",
                    "All three runes collected and deposited opens the floor below.",
                ],
                "teams": [
                    {"label": "Symbol Readers (split 1 per shaft)", "role": "Each descend a shaft, match their symbol to the correct Hive Knight, kill it, deposit rune"},
                ],
            },
            {
                "name": "Zulmak, Instrument of Torment",
                "weaponTypes": ["Sword", "Rocket Launcher"],
                "elements": ["Solar", "Arc", "Void"],
                "exotics": ["Lament"],
                "tip": "Must charge all three elemental buffs before dealing damage. Same rune mechanic, now on the boss.",
                "steps": [
                    "Three Hive Knights around the arena each hold an elemental rune — Solar, Arc, Void.",
                    "Kill each knight and pick up their rune — grants a brief elemental buff.",
                    "All three rune holders must stand in Zulmak's circle simultaneously to stun him.",
                    "Burst damage during stun window with Sword or rockets — repeat until dead.",
                ],
                "teams": [
                    {"label": "Rune Carriers (1 each)", "role": "Pick up Solar, Arc, or Void rune and converge on Zulmak simultaneously to trigger stun"},
                ],
            },
        ],
    },
    "prophecy": {
        "name": "Prophecy",
        "type": "dungeon",
        "activityHash": 1077850348,
        "videoUrl": "https://www.youtube.com/results?search_query=Prophecy+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "The Phalanx Echo",
                "weaponTypes": ["Rocket Launcher", "Sniper Rifle"],
                "elements": ["Void", "Arc"],
                "exotics": ["Xenophage"],
                "tip": "Collect Motes from Taken adds — deposit Light or Dark Motes to charge the corresponding pillar.",
                "steps": [
                    "Kill Taken adds — they drop either Light Motes or Dark Motes.",
                    "Two pillars on opposite ends of the room: Light and Dark. Deposit matching motes.",
                    "Depositing enough charges the pillar and weakens the Phalanx Echo.",
                    "Burst the boss during the exposed window. Repeat until dead.",
                ],
                "teams": [],
            },
            {
                "name": "Kell Echo",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void"],
                "exotics": ["Xenophage"],
                "tip": "Same mote mechanic but the boss moves between platforms mid-encounter. Stay mobile.",
                "steps": [
                    "Same Light/Dark mote mechanic — collect from Taken adds, deposit to matching pillar.",
                    "Kell Echo teleports between platforms — deposit quickly before he relocates.",
                    "After depositing motes on a platform, all three burst him with heavy before he teleports.",
                    "Void surge is active — full Void loadout maximizes DPS.",
                ],
                "teams": [],
            },
        ],
    },
    "grasp-of-avarice": {
        "name": "Grasp of Avarice",
        "type": "dungeon",
        "activityHash": 4078656646,
        "videoUrl": "https://www.youtube.com/results?search_query=Grasp+of+Avarice+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Phry'zhia the Insatiable",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Arc", "Solar"],
                "exotics": ["Gjallarhorn"],
                "tip": "Collect Burden of Riches stacks from Engrams — deposit at the boss to strip her shield.",
                "steps": [
                    "Kill Fallen adds — they drop Engrams that give Burden of Riches stacks.",
                    "Stacks cap at 5 — deposit at Phry'zhia's shield generator before they expire.",
                    "Five deposits total breaks her shield and opens the damage window.",
                    "Burst with rockets or Machine Gun — she re-shields after each DPS phase.",
                ],
                "teams": [],
            },
            {
                "name": "Avarokk, the Covetous",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Arc", "Solar"],
                "exotics": ["Gjallarhorn", "Thunderlord"],
                "tip": "Final boss — same Burden of Riches mechanic but two shield generators. Split collection.",
                "steps": [
                    "Same Engram → Burden of Riches stacks mechanic, now with two separate shield generators.",
                    "Split the team: half deposit on left generator, half on right — both must break simultaneously.",
                    "Both shields down → DPS phase. LFRs and rockets for burst.",
                    "Avarokk gains adds each cycle — clear them quickly to maintain Engram pickup efficiency.",
                ],
                "teams": [
                    {"label": "Left Generator (1-2p)", "role": "Collect Engrams on left side → deposit Burden of Riches stacks into left shield generator"},
                    {"label": "Right Generator (1-2p)", "role": "Collect Engrams on right side → deposit into right shield generator — both must break together"},
                ],
            },
        ],
    },
    "duality": {
        "name": "Duality",
        "type": "dungeon",
        "activityHash": 2823159265,
        "videoUrl": "https://www.youtube.com/results?search_query=Duality+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Caiatl's Vault",
                "weaponTypes": ["Rocket Launcher", "Sniper Rifle"],
                "elements": ["Solar", "Void"],
                "exotics": ["Gjallarhorn"],
                "tip": "Two realms — physical and shadow. Kill Bell Keepers in shadow realm to ring bells and open vault.",
                "steps": [
                    "Stand in a shadow portal to enter the shadow realm — limited time before you die.",
                    "Kill Bell Keepers in the shadow realm — their death rings the bell in the physical realm.",
                    "Bell ringing opens the vault door in the physical realm briefly — run through.",
                    "Three bells must be rung in sequence to complete the encounter.",
                ],
                "teams": [
                    {"label": "Shadow Team (1-2p)", "role": "Enter shadow portals → kill Bell Keepers → ring bells to open doors for physical team"},
                    {"label": "Physical Team (1-2p)", "role": "Stay alive → sprint through doors as bells open → handle adds in physical realm"},
                ],
            },
            {
                "name": "Nightmare of Caiatl",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Solar"],
                "exotics": ["Gjallarhorn", "Whisper of the Worm"],
                "tip": "Kill shadow realm Cabal to charge a bell. Ring it to drop boss immunity. Burst during window.",
                "steps": [
                    "Caiatl is immune in the physical realm — enter the shadow realm to progress.",
                    "Kill shadow realm Cabal to collect bell charges — deposit charges at the shadow bell.",
                    "Ringing the shadow bell briefly exposes Caiatl in the physical realm.",
                    "All players burst Caiatl during the exposed window — Solar weapons recommended.",
                ],
                "teams": [
                    {"label": "Shadow Runners (2p)", "role": "Enter shadow realm → kill Cabal for bell charges → deposit and ring bell"},
                    {"label": "Physical DPS (1p)", "role": "Stay in physical realm → burst Caiatl the moment she's exposed after the bell rings"},
                ],
            },
        ],
    },
    "vespers-host": {
        "name": "Vesper's Host",
        "type": "dungeon",
        "activityHash": 300092127,
        "videoUrl": "https://www.youtube.com/results?search_query=Vespers+Host+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Raneiks Unified",
                "weaponTypes": ["Machine Gun", "Rocket Launcher"],
                "elements": ["Arc", "Void"],
                "exotics": ["Thunderlord"],
                "tip": "Power the three generators by carrying Arc Charges — then burst the boss during the open window.",
                "steps": [
                    "Fallen adds drop Arc Charges — pick them up and deposit in one of three generators.",
                    "All three generators must be powered simultaneously to open Raneiks's damage window.",
                    "Coordinate deposits — stagger charges so all three go live at the same time.",
                    "Arc surge is active — Arc weapons and Arc subclass deal bonus damage throughout.",
                ],
                "teams": [
                    {"label": "Charge Runners (3p, one per generator)", "role": "Collect Arc Charges from adds → deposit in assigned generator simultaneously on callout"},
                ],
            },
            {
                "name": "Atraks-Sovereign",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Arc"],
                "exotics": ["Thunderlord"],
                "tip": "Same generator mechanic as Raneiks but Atraks splits into copies. Kill the real one.",
                "steps": [
                    "Atraks splits into multiple copies — only the real one takes full damage.",
                    "Power the three generators to force Atraks out of his immunity state.",
                    "Find the real copy by looking for the glowing weak point — burst him hard.",
                    "Arc surge remains active — Thunderlord and Arc rockets are best in slot.",
                ],
                "teams": [
                    {"label": "Generator Team (2p)", "role": "Charge and deposit Arc Charges to power all three generators simultaneously"},
                    {"label": "Boss Caller (1p)", "role": "Identify real Atraks copy during damage window and call it for the team"},
                ],
            },
        ],
    },
    "equilibrium": {
        "name": "Equilibrium",
        "type": "dungeon",
        "activityHash": 2727361621,
        "videoUrl": "https://www.youtube.com/results?search_query=Equilibrium+dungeon+guide+destiny+2",
        "encounters": [
            {
                "name": "Encounter 1",
                "weaponTypes": ["Rocket Launcher", "Machine Gun"],
                "elements": ["Void", "Solar"],
                "exotics": [],
                "tip": "Edge of Fate dungeon — coordinate mechanics across the split arena.",
                "steps": [
                    "Learn the core mechanic in this encounter — it repeats throughout.",
                    "Assign roles before pulling: at least one player on mechanic duty at all times.",
                ],
                "teams": [],
            },
            {
                "name": "Final Boss",
                "weaponTypes": ["Linear Fusion Rifle", "Rocket Launcher"],
                "elements": ["Void", "Solar"],
                "exotics": ["Heirloom"],
                "tip": "Heirloom exotic bow drops from this boss. Trigger the DPS window via the encounter mechanic.",
                "steps": [
                    "Complete the boss mechanic to open the damage window.",
                    "Burst the boss with LFRs or rockets during every exposed phase.",
                    "Heirloom has a chance to drop on clear — farm on subsequent runs.",
                ],
                "teams": [],
            },
        ],
    },
}

# ── Prompts ───────────────────────────────────────────────────────────────────

ADVISOR_SYSTEM_PROMPT = (
    "You are a Destiny 2 fireteam analyst. Be brutally concise.\n\n"
    "Return EXACTLY 4 bullet points. Each bullet must be under 15 words.\n"
    "Format: '• [label]: [action or observation]'\n"
    "Cover exactly: (1) champion mod gaps, (2) support build presence, "
    "(3) element or debuff weakness, (4) one specific swap or positive call-out.\n"
    "No prose. No intro. No markdown beyond the bullets. "
    "Name specific exotics and subclasses in swap suggestions."
)


# ── Models ────────────────────────────────────────────────────────────────────


class TeamRole(BaseModel):
    label: str
    role: str


class EncounterCard(BaseModel):
    name: str
    imageUrl: str | None
    weaponTypes: list[str]
    elements: list[str]
    exotics: list[str]
    tip: str
    steps: list[str] = []
    teams: list[TeamRole] = []
    vaultMatches: list[str] = []


class ActivityInfo(BaseModel):
    id: str
    name: str
    type: str  # "raid" | "dungeon"
    imageUrl: str | None
    videoUrl: str
    encounters: list[EncounterCard]


class FireteamAnalyzeRequest(BaseModel):
    members: list[str]  # Bungie names: ["Name#1234"] — max 5, self auto-included
    membership_type: int
    membership_id: str
    activity_id: str | None = None  # optional key from ACTIVITIES dict


class MemberProfile(BaseModel):
    displayName: str
    className: str = "Unknown"
    subclassElement: str = "Unknown"
    exoticWeapon: str | None = None
    exoticArmor: str | None = None
    weaponElements: list[str] = []
    isCurrentUser: bool = False
    error: str | None = None


class FireteamAnalysisResponse(BaseModel):
    members: list[MemberProfile]
    elementCoverage: list[str]
    missingElements: list[str]
    classCoverage: list[str]
    claudeAnalysis: str
    encounterCards: list[EncounterCard]


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _extract_from_equipment(
    display_name: str,
    membership_type: int,
    membership_id: str,
    is_self: bool,
    access_token: str | None = None,
) -> MemberProfile:
    """Fetch a player's equipped loadout and extract composition-relevant fields."""
    try:
        if access_token:
            profile_data = await bungie_api.get_profile(membership_type, membership_id, access_token)
        else:
            profile_data = await bungie_api.get_public_equipment(membership_type, membership_id)

        chars_raw = profile_data.get("characters", {}).get("data", {})
        equip_raw = profile_data.get("characterEquipment", {}).get("data", {})

        if not chars_raw:
            return MemberProfile(displayName=display_name, isCurrentUser=is_self, error="Profile is private")

        # Most recently played character
        primary_char_id = max(chars_raw, key=lambda cid: chars_raw[cid].get("dateLastPlayed", ""))
        class_type = chars_raw[primary_char_id].get("classType", -1)
        class_name = CLASS_NAMES.get(class_type, "Unknown")

        items = equip_raw.get(primary_char_id, {}).get("items", [])

        subclass_element = "Unknown"
        exotic_weapon: str | None = None
        exotic_armor: str | None = None
        weapon_elements: list[str] = []

        for item in items:
            item_hash = item.get("itemHash")
            if not item_hash:
                continue
            raw = await manifest.get_item(item_hash)
            if not raw:
                continue
            defn = json.loads(raw)
            bucket = defn.get("inventory", {}).get("bucketTypeHash")
            damage = defn.get("defaultDamageType", -1)
            tier = defn.get("inventory", {}).get("tierType", 0)
            name = defn.get("displayProperties", {}).get("name", "")

            if bucket == SUBCLASS_BUCKET:
                subclass_element = DAMAGE_TYPE.get(damage, "Unknown")
            elif bucket in WEAPON_BUCKETS:
                elem = DAMAGE_TYPE.get(damage, "Kinetic")
                weapon_elements.append(elem if elem != "Prismatic" else "Kinetic")
                if tier == 6 and not exotic_weapon:
                    exotic_weapon = name
            elif bucket in ARMOR_BUCKETS:
                if tier == 6 and not exotic_armor:
                    exotic_armor = name

        return MemberProfile(
            displayName=display_name,
            className=class_name,
            subclassElement=subclass_element,
            exoticWeapon=exotic_weapon,
            exoticArmor=exotic_armor,
            weaponElements=weapon_elements,
            isCurrentUser=is_self,
        )

    except Exception as e:
        return MemberProfile(displayName=display_name, isCurrentUser=is_self, error=str(e)[:120])


async def _lookup_and_extract(name_with_code: str) -> MemberProfile:
    """Parse 'Name#1234', search Bungie API, return MemberProfile."""
    if "#" not in name_with_code:
        return MemberProfile(displayName=name_with_code, error="Use Name#1234 format")

    parts = name_with_code.rsplit("#", 1)
    display_name, code_str = parts[0].strip(), parts[1].strip()
    try:
        code = int(code_str)
    except ValueError:
        return MemberProfile(displayName=name_with_code, error="Code must be a number (Name#1234)")

    result = await bungie_api.search_player_by_bungie_name(display_name, code)
    if not result:
        return MemberProfile(displayName=name_with_code, error="Guardian not found")

    mem_type = result.get("membershipType") or result.get("crossSaveOverride", 3)
    mem_id = result.get("membershipId", "")
    return await _extract_from_equipment(name_with_code, mem_type, mem_id, is_self=False)


def _build_context(members: list[MemberProfile]) -> str:
    lines = ["Fireteam composition:"]
    for m in members:
        if m.error:
            lines.append(f"- {m.displayName} [ERROR: {m.error}]")
            continue
        tag = " [SELF]" if m.isCurrentUser else ""
        exotic_armor = f"Exotic Armor: {m.exoticArmor}" if m.exoticArmor else "Exotic Armor: none"
        exotic_wpn  = f"Exotic Weapon: {m.exoticWeapon}" if m.exoticWeapon else "Exotic Weapon: none"
        weapons     = f"Weapon elements: {', '.join(m.weaponElements) or 'unknown'}"
        lines.append(
            f"- {m.displayName}{tag} — {m.className}, {m.subclassElement} | "
            f"{exotic_armor} | {exotic_wpn} | {weapons}"
        )

    valid = [m for m in members if not m.error]
    all_elements = sorted({m.subclassElement for m in valid if m.subclassElement not in ("Unknown", "Prismatic")})
    missing = sorted(ALL_ELEMENTS - set(all_elements))
    classes = sorted({m.className for m in valid if m.className != "Unknown"})

    lines.append(f"\nElement coverage: {', '.join(all_elements) or 'none'}")
    lines.append(f"Missing elements: {', '.join(missing) or 'none'}")
    lines.append(f"Classes present: {', '.join(classes) or 'none'}")
    return "\n".join(lines)


async def _resolve_activity_image(activity_hash: int) -> str | None:
    try:
        raw = await manifest.get_activity(activity_hash)
        if raw:
            pgcr = json.loads(raw).get("pgcrImage")
            if pgcr:
                return f"https://www.bungie.net{pgcr}"
    except Exception:
        pass
    return None


async def _get_vault_weapons(
    membership_type: int,
    membership_id: str,
    access_token: str,
) -> list[dict]:
    """Fetch all legendary/exotic weapons from the user's vault and character bags.
    Returns [{name, weaponType, element, isExotic}]. Never raises — returns [] on any failure."""
    try:
        profile = await bungie_api.get_profile_with_vault(membership_type, membership_id, access_token)

        # Pre-filter by bucket hash so we only manifest-lookup actual weapons
        seen: set[int] = set()
        weapon_hashes: list[int] = []

        vault_items = profile.get("profileInventory", {}).get("data", {}).get("items", [])
        for item in vault_items:
            h = item.get("itemHash")
            if h and item.get("bucketHash") in WEAPON_BUCKETS and h not in seen:
                seen.add(h)
                weapon_hashes.append(h)

        char_inventories = profile.get("characterInventories", {}).get("data", {})
        for char_data in char_inventories.values():
            for item in char_data.get("items", []):
                h = item.get("itemHash")
                if h and item.get("bucketHash") in WEAPON_BUCKETS and h not in seen:
                    seen.add(h)
                    weapon_hashes.append(h)

        if not weapon_hashes:
            return []

        raw_items = await manifest.get_items_batch(weapon_hashes)

        weapons: list[dict] = []
        for raw in raw_items:
            defn = json.loads(raw)
            tier = defn.get("inventory", {}).get("tierType", 0)
            if tier < 5:  # skip below legendary
                continue
            damage = defn.get("defaultDamageType", -1)
            name = defn.get("displayProperties", {}).get("name", "")
            item_type = defn.get("itemTypeDisplayName", "")
            if not name or not item_type:
                continue
            weapons.append({
                "name": name,
                "weaponType": item_type,
                "element": DAMAGE_TYPE.get(damage, "Kinetic"),
                "isExotic": tier == 6,
            })

        return weapons
    except Exception:
        return []


def _match_weapons_to_encounter(
    vault_weapons: list[dict],
    weapon_types: list[str],
    elements: list[str],
    max_results: int = 4,
) -> list[str]:
    """Return formatted strings for vault weapons matching encounter weapon types.
    Sorts exotics and element-matched weapons to the top."""
    scored: list[tuple[tuple, dict]] = []
    for w in vault_weapons:
        wtype = w["weaponType"].lower()
        type_match = any(
            enc_wt.lower() in wtype or wtype in enc_wt.lower()
            for enc_wt in weapon_types
        )
        if not type_match:
            continue
        elem_match = w["element"] in elements if elements else False
        score = (w["isExotic"] and elem_match, w["isExotic"], elem_match)
        scored.append((score, w))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: list[str] = []
    for _, w in scored[:max_results]:
        prefix = "★ " if w["isExotic"] else ""
        elem = f" [{w['element']}]" if w["element"] not in ("Kinetic", "Unknown") else ""
        results.append(f"{prefix}{w['name']}{elem}")
    return results


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/fireteam/search")
async def search_guardians(query: str = Query(..., min_length=2)):
    """Autocomplete endpoint — wraps Bungie's SearchByGlobalNamePrefix."""
    results = await bungie_api.search_by_name_prefix(query)
    print(f"[search] query={query!r} → {len(results)} results, sample={results[:1]}")
    suggestions: list[str] = []
    for r in results[:8]:
        name = r.get("bungieGlobalDisplayName", "")
        code = r.get("bungieGlobalDisplayNameCode")
        if name and code is not None:
            suggestions.append(f"{name}#{code:04d}")
    return {"suggestions": suggestions}


@router.get("/fireteam/activities", response_model=list[ActivityInfo])
async def get_activities():
    """Return all available raids/dungeons with encounter breakdown and resolved images."""
    result: list[ActivityInfo] = []
    for act_id, act in ACTIVITIES.items():
        image_url = await _resolve_activity_image(act["activityHash"])
        result.append(ActivityInfo(
            id=act_id,
            name=act["name"],
            type=act["type"],
            imageUrl=image_url,
            videoUrl=act["videoUrl"],
            encounters=[EncounterCard(imageUrl=image_url, **e) for e in act["encounters"]],
        ))
    return result


class LastFireteamResponse(BaseModel):
    members: list[str]          # "Name#1234" strings, excludes self
    activityMode: str           # human-readable mode name
    activityDate: str           # ISO timestamp of the activity


@router.get("/fireteam/last-activity", response_model=LastFireteamResponse)
async def get_last_fireteam(
    membership_type: int,
    membership_id: str,
    authorization: str = Header(...),
):
    """Fetch the PGCR for the most recent completed activity and return the other players."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    MODE_NAMES: dict[int, str] = {
        4: "Raid", 16: "Nightfall", 18: "Strike", 46: "Nightfall",
        5: "Crucible", 10: "Control", 12: "Clash", 15: "Crimson Doubles",
        31: "Supremacy", 37: "Survival", 38: "Countdown", 43: "Trials of Osiris",
        84: "Dungeon", 82: "Dungeon",
    }

    profile_data = await bungie_api.get_profile(membership_type, membership_id, access_token)
    chars_raw = profile_data.get("characters", {}).get("data", {})
    if not chars_raw:
        raise HTTPException(status_code=404, detail="No characters found")

    primary_char_id = max(chars_raw, key=lambda cid: chars_raw[cid].get("dateLastPlayed", ""))

    try:
        hist = await bungie_api.get_activity_history(
            membership_type, membership_id, primary_char_id, access_token,
            mode=0, count=10, page=0,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Activity history fetch failed: {e}")

    activities = hist.get("activities") or []
    for act in activities:
        iid = str(act.get("activityDetails", {}).get("instanceId", ""))
        if not iid or iid == "0":
            continue
        mode_val = act.get("activityDetails", {}).get("mode", 0)
        period = act.get("period", "")

        try:
            pgcr = await bungie_api.get_pgcr(iid)
        except Exception:
            continue

        entries = pgcr.get("entries", [])
        others: list[str] = []
        for entry in entries:
            user_info = entry.get("player", {}).get("destinyUserInfo", {})
            mid = str(user_info.get("membershipId", ""))
            if not mid or mid == membership_id:
                continue
            global_name = user_info.get("bungieGlobalDisplayName", "")
            code = user_info.get("bungieGlobalDisplayNameCode")
            if global_name and code is not None:
                others.append(f"{global_name}#{code:04d}")
            elif global_name:
                others.append(global_name)

        if others:
            return LastFireteamResponse(
                members=others,
                activityMode=MODE_NAMES.get(mode_val, f"Activity (mode {mode_val})"),
                activityDate=period,
            )

    raise HTTPException(status_code=404, detail="No recent fireteam activity found")


@router.post("/fireteam/analyze", response_model=FireteamAnalysisResponse)
async def analyze_fireteam(
    body: FireteamAnalyzeRequest,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    access_token = authorization.removeprefix("Bearer ")

    if len(body.members) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 additional members (6 total with self)")

    # Fetch self, named members, and vault all in parallel
    self_task = _extract_from_equipment(
        "You", body.membership_type, body.membership_id, is_self=True, access_token=access_token
    )
    member_tasks = [_lookup_and_extract(name) for name in body.members]
    vault_task = _get_vault_weapons(body.membership_type, body.membership_id, access_token)

    gathered = await asyncio.gather(self_task, *member_tasks, vault_task)
    all_members: list[MemberProfile] = [gathered[0]] + list(gathered[1:-1])
    vault_weapons: list[dict] = gathered[-1]

    # Coverage metrics
    valid = [m for m in all_members if not m.error]
    element_coverage = sorted({m.subclassElement for m in valid if m.subclassElement not in ("Unknown", "Prismatic")})
    missing_elements = sorted(ALL_ELEMENTS - set(element_coverage))
    class_coverage = sorted({m.className for m in valid if m.className != "Unknown"})

    # Resolve activity encounter cards + append context to Claude message
    encounter_cards: list[EncounterCard] = []
    activity_context = ""
    if body.activity_id and body.activity_id in ACTIVITIES:
        act = ACTIVITIES[body.activity_id]
        image_url = await _resolve_activity_image(act["activityHash"])
        encounter_cards = [
            EncounterCard(
                imageUrl=image_url,
                vaultMatches=_match_weapons_to_encounter(vault_weapons, e["weaponTypes"], e["elements"]),
                **e,
            )
            for e in act["encounters"]
        ]
        boss = act["encounters"][-1]
        boss_vault = _match_weapons_to_encounter(vault_weapons, boss["weaponTypes"], boss["elements"], max_results=3)
        activity_context = (
            f"\n\nActivity: {act['name']} ({act['type']})\n"
            f"Final encounter ({boss['name']}): {boss['tip']}\n"
            f"Key weapons for this activity: {', '.join(boss['weaponTypes'][:2])}\n"
        )
        if boss_vault:
            activity_context += f"Player's vault has matching weapons: {', '.join(boss_vault)}\n"
            activity_context += "Name these specific vault weapons in your swap bullet — be direct about what to equip."
        else:
            activity_context += "Factor activity weapon requirements into your swap bullet."

    # Claude analysis
    context = _build_context(all_members) + activity_context
    claude_analysis = ""
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=ADVISOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
        )
        claude_analysis = response.content[0].text
    except Exception:
        parts = []
        if missing_elements:
            parts.append(f"• Element gap: Missing {', '.join(missing_elements)}.")
        if len(class_coverage) < min(3, len(valid)):
            parts.append("• Class redundancy: Multiple members share the same class.")
        if not parts:
            parts.append("• Composition looks balanced for standard content.")
        claude_analysis = "\n".join(parts)

    return FireteamAnalysisResponse(
        members=all_members,
        elementCoverage=element_coverage,
        missingElements=missing_elements,
        classCoverage=class_coverage,
        claudeAnalysis=claude_analysis,
        encounterCards=encounter_cards,
    )
