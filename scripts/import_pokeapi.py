# scripts/import_pokeapi.py - Build chatbot/data/pokedex.json from PokeAPI's CSV dump
#
# Usage (from project root):
#   python scripts/import_pokeapi.py            # download missing CSVs, rebuild pokedex.json
#   python scripts/import_pokeapi.py --refresh  # re-download every CSV first
#
# Source: https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv (free, no API key).
# CSVs are cached in data/pokeapi_cache/ (gitignored).

import argparse
import csv
import difflib
import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "pokeapi_cache"
OUTPUT_PATH = PROJECT_ROOT / "chatbot" / "data" / "pokedex.json"
CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/{}.csv"

CSV_FILES = [
    "pokemon", "pokemon_species", "pokemon_species_names", "pokemon_species_flavor_text",
    "pokemon_stats", "pokemon_types", "types", "type_efficacy", "pokemon_evolution",
    "evolution_triggers", "moves", "move_names", "move_effect_prose", "items", "item_names",
    "item_prose", "item_categories", "pokemon_moves", "version_groups", "versions",
    "version_names", "generations", "location_names", "abilities", "ability_names",
    "ability_prose", "pokemon_abilities", "pokemon_egg_groups", "egg_group_prose", "growth_rate_prose",
    "pokemon_forms", "pokemon_form_names",
]

ENGLISH = "9"
STAT_KEYS = {"1": "hp", "2": "attack", "3": "defense", "4": "sp_attack", "5": "sp_defense", "6": "speed"}
DAMAGE_CLASSES = {"1": "status", "2": "physical", "3": "special"}
REGIONS = {
    1: "Kanto", 2: "Johto", 3: "Hoenn", 4: "Sinnoh", 5: "Unova",
    6: "Kalos", 7: "Alola", 8: "Galar", 9: "Paldea",
}
# Japanese-only and competitive-only releases have incomplete learnsets
SKIPPED_LEARNSET_GROUPS = {"red-green-japan", "blue-japan", "champions"}
PREFERRED_LEARNSET_GROUP = "scarlet-violet"
# Evolution triggers that need a hand-written description ("" = the conditions say it all)
SPECIAL_TRIGGERS = {
    "shed": "when Nincada evolves with a free party slot and a spare Poke Ball",
    "spin": "by spinning around",
    "tower-of-darkness": "by training in the Tower of Darkness",
    "tower-of-waters": "by training in the Tower of Waters",
    "three-critical-hits": "after landing three critical hits in one battle",
    "take-damage": "",
    "agile-style-move": "after using its signature move in Agile Style 20 times",
    "strong-style-move": "after using its signature move in Strong Style 20 times",
    "recoil-damage": "",
    "use-move": "",
    "in-battle-level-up": "on level up during a battle",
    "three-defeated-bisharp": "after defeating three Bisharp that hold a Leader's Crest",
    "gimmighoul-coins": "after collecting 999 Gimmighoul Coins",
    "meltan-candies": "by feeding it 400 Meltan Candies in Pokemon GO",
}
MEGA_STONE_CATEGORY = "44"
PRIMAL_ORBS = {"groudon": "red-orb", "kyogre": "blue-orb"}
# Mega Evolves by knowing a move instead of holding a stone
STONELESS_MEGAS = {"rayquaza": "dragon-ascent"}
# Not flagged in PokeAPI; the community definition (600 base stat total, three-stage line)
PSEUDO_LEGENDARIES = [
    "dragonite", "tyranitar", "salamence", "metagross", "garchomp",
    "hydreigon", "goodra", "kommo-o", "dragapult", "baxcalibur",
]
STARTERS = {
    1: ["bulbasaur", "charmander", "squirtle"],
    2: ["chikorita", "cyndaquil", "totodile"],
    3: ["treecko", "torchic", "mudkip"],
    4: ["turtwig", "chimchar", "piplup"],
    5: ["snivy", "tepig", "oshawott"],
    6: ["chespin", "fennekin", "froakie"],
    7: ["rowlet", "litten", "popplio"],
    8: ["grookey", "scorbunny", "sobble"],
    9: ["sprigatito", "fuecoco", "quaxly"],
}


def download(refresh: bool):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for name in CSV_FILES:
        path = CACHE_DIR / f"{name}.csv"
        if path.exists() and not refresh:
            continue
        print(f"Downloading {name}.csv")
        urllib.request.urlretrieve(CSV_URL.format(name), path)


def read(name):
    with open(CACHE_DIR / f"{name}.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def english_names(name, id_field, value_field="name"):
    return {r[id_field]: r[value_field] for r in read(name) if r["local_language_id"] == ENGLISH}


def clean_prose(text, effect_chance=""):
    """Strip PokeAPI markup like [paralyze]{mechanic:paralysis} and fill $effect_chance."""
    def replace_link(m):
        label, target = m.group(1), m.group(2)
        return label or target.split(":")[-1].replace("-", " ")

    text = re.sub(r"\[([^\]]*)\]\{([^}]*)\}", replace_link, text or "")
    text = text.replace("$effect_chance", effect_chance or "some")
    return re.sub(r"\s+", " ", text).strip()


def article(word):
    return f"an {word}" if word[:1].lower() in "aeiou" else f"a {word}"


def to_int(value):
    return int(value) if value not in ("", None) else None


def build():
    # Skip Stellar (Tera-only, no matchups) and the 10000+ placeholder types
    type_rows = [r for r in read("types") if int(r["id"]) < 10000 and r["identifier"] != "stellar"]
    type_slug = {r["id"]: r["identifier"] for r in type_rows}
    types = {r["identifier"]: {"name": r["identifier"].title(), "generation": int(r["generation_id"])}
             for r in type_rows}

    type_chart = defaultdict(dict)
    for r in read("type_efficacy"):
        factor = int(r["damage_factor"]) / 100
        if factor != 1 and r["damage_type_id"] in type_slug and r["target_type_id"] in type_slug:
            type_chart[type_slug[r["damage_type_id"]]][type_slug[r["target_type_id"]]] = factor

    # Games per generation
    version_names = english_names("version_names", "version_id")
    group_rows = read("version_groups")
    group_slug = {r["id"]: r["identifier"] for r in group_rows}
    group_order = {r["identifier"]: int(r["order"]) for r in group_rows}
    group_generation = {r["id"]: int(r["generation_id"]) for r in group_rows}
    group_names = defaultdict(list)
    games_by_generation = defaultdict(list)
    for r in read("versions"):
        group = group_slug[r["version_group_id"]]
        name = version_names.get(r["id"], r["identifier"].title())
        group_names[group].append(name)
        if group not in SKIPPED_LEARNSET_GROUPS:
            games_by_generation[group_generation[r["version_group_id"]]].append(name)

    # Moves
    move_names = english_names("move_names", "move_id")
    move_effects = {r["move_effect_id"]: r["short_effect"]
                    for r in read("move_effect_prose") if r["local_language_id"] == ENGLISH}
    move_slug = {}
    moves = {}
    for r in read("moves"):
        if int(r["id"]) >= 10000 or r["type_id"] not in type_slug:
            continue  # Shadow moves and other non-standard entries
        move_slug[r["id"]] = r["identifier"]
        moves[r["identifier"]] = {
            "name": move_names.get(r["id"], r["identifier"].replace("-", " ").title()),
            "type": type_slug[r["type_id"]],
            "damage_class": DAMAGE_CLASSES.get(r["damage_class_id"], "unknown"),
            "power": to_int(r["power"]),
            "accuracy": to_int(r["accuracy"]),
            "pp": to_int(r["pp"]),
            "priority": int(r["priority"] or 0),
            "generation": int(r["generation_id"]),
            "effect": clean_prose(move_effects.get(r["effect_id"], ""), r["effect_chance"]),
        }

    # Items
    item_names = english_names("item_names", "item_id")
    item_effects = {r["item_id"]: r["short_effect"]
                    for r in read("item_prose") if r["local_language_id"] == ENGLISH}
    item_categories = {r["id"]: r["identifier"] for r in read("item_categories")}
    item_slug = {}
    items = {}
    for r in read("items"):
        if r["id"] not in item_names:
            continue  # Items without an English name are unreleased/placeholder data
        item_slug[r["id"]] = r["identifier"]
        items[r["identifier"]] = {
            "name": item_names[r["id"]],
            "category": item_categories.get(r["category_id"], "").replace("-", " "),
            "cost": to_int(r["cost"]),
            "effect": clean_prose(item_effects.get(r["id"], "")),
        }

    # Species
    species_rows = read("pokemon_species")
    species_slug = {r["id"]: r["identifier"] for r in species_rows}
    species_names = {}
    genera = {}
    for r in read("pokemon_species_names"):
        if r["local_language_id"] == ENGLISH:
            species_names[r["pokemon_species_id"]] = r["name"]
            genera[r["pokemon_species_id"]] = r["genus"]

    flavor = {}  # latest English entry per species
    for r in read("pokemon_species_flavor_text"):
        if r["language_id"] == ENGLISH:
            prev = flavor.get(r["species_id"])
            if prev is None or int(r["version_id"]) > prev[0]:
                flavor[r["species_id"]] = (int(r["version_id"]), " ".join(r["flavor_text"].split()))

    # Default form of each species (e.g. deoxys-normal for deoxys)
    default_pokemon = {r["species_id"]: r for r in read("pokemon") if r["is_default"] == "1"}
    pokemon_species_id = {r["id"]: r["species_id"] for r in default_pokemon.values()}
    # Mega Evolutions and Primal Reversions get their own types, stats and abilities
    mega_rows = [r for r in read("pokemon") if re.search(r"-(mega|primal)(-|$)", r["identifier"])]
    loaded_ids = set(pokemon_species_id) | {r["id"] for r in mega_rows}

    stats = defaultdict(dict)
    ev_yield = defaultdict(dict)
    for r in read("pokemon_stats"):
        if r["pokemon_id"] in loaded_ids:
            stats[r["pokemon_id"]][STAT_KEYS[r["stat_id"]]] = int(r["base_stat"])
            if int(r["effort"] or 0):
                ev_yield[r["pokemon_id"]][STAT_KEYS[r["stat_id"]]] = int(r["effort"])

    # Abilities
    ability_names = english_names("ability_names", "ability_id")
    ability_effects = {r["ability_id"]: r["short_effect"]
                       for r in read("ability_prose") if r["local_language_id"] == ENGLISH}
    ability_slug = {r["id"]: r["identifier"] for r in read("abilities") if r["id"] in ability_names}
    abilities = {slug: {"name": ability_names[aid], "effect": clean_prose(ability_effects.get(aid, ""))}
                 for aid, slug in ability_slug.items()}
    pokemon_abilities = defaultdict(list)
    for r in sorted(read("pokemon_abilities"), key=lambda r: int(r["slot"])):
        if r["pokemon_id"] in loaded_ids and r["ability_id"] in ability_slug:
            pokemon_abilities[r["pokemon_id"]].append(
                {"ability": ability_slug[r["ability_id"]], "hidden": r["is_hidden"] == "1"})

    # Breeding and training
    egg_group_names = english_names("egg_group_prose", "egg_group_id")
    egg_groups = defaultdict(list)
    for r in read("pokemon_egg_groups"):
        egg_groups[r["species_id"]].append(egg_group_names.get(r["egg_group_id"], ""))
    growth_rates = english_names("growth_rate_prose", "growth_rate_id")

    pokemon_types = defaultdict(list)
    for r in sorted(read("pokemon_types"), key=lambda r: int(r["slot"])):
        if r["pokemon_id"] in loaded_ids:
            pokemon_types[r["pokemon_id"]].append(type_slug[r["type_id"]])

    megas = build_megas(mega_rows, species_slug, items, read("items"), stats, pokemon_types,
                        pokemon_abilities, ev_yield)
    evolutions = build_evolutions(species_slug, item_slug, items, move_slug, moves, type_slug)
    learnsets = build_learnsets(pokemon_species_id, species_slug, move_slug, group_slug, group_order, group_names)

    pokemon = {}
    for r in species_rows:
        sid = r["id"]
        form = default_pokemon.get(sid)
        if form is None:
            continue
        slug = r["identifier"]
        pokemon[slug] = {
            "id": int(sid),
            "name": species_names.get(sid, slug.title()),
            "genus": genera.get(sid, ""),
            "generation": int(r["generation_id"]),
            "types": pokemon_types[form["id"]],
            "stats": stats[form["id"]],
            "height_m": int(form["height"]) / 10,
            "weight_kg": int(form["weight"]) / 10,
            "legendary": r["is_legendary"] == "1",
            "mythical": r["is_mythical"] == "1",
            "baby": r["is_baby"] == "1",
            "evolves_from": species_slug.get(r["evolves_from_species_id"]),
            "evolution_method": evolutions.get(sid),
            "evolution_chain": int(r["evolution_chain_id"]) if r["evolution_chain_id"] else None,
            "flavor_text": flavor.get(sid, (0, ""))[1],
            "abilities": pokemon_abilities[form["id"]],
            "ev_yield": ev_yield[form["id"]],
            "catch_rate": to_int(r["capture_rate"]),
            "base_friendship": to_int(r["base_happiness"]),
            "base_experience": to_int(form["base_experience"]),
            "growth_rate": growth_rates.get(r["growth_rate_id"], ""),
            "egg_groups": egg_groups[sid],
            # Eighths female; -1 = genderless
            "gender_rate": to_int(r["gender_rate"]),
            "egg_cycles": to_int(r["hatch_counter"]),
            "learnset": learnsets.get(slug),
            "megas": megas.get(slug, []),
        }

    generations = {
        str(g): {
            "region": REGIONS[g],
            "games": games_by_generation[g],
            "starters": STARTERS[g],
            "pokemon_count": sum(1 for p in pokemon.values() if p["generation"] == g),
        }
        for g in REGIONS
    }

    return {
        "meta": {
            "source": "https://github.com/PokeAPI/pokeapi (data/v2/csv)",
            "generated": date.today().isoformat(),
            "notes": "Default forms only; learnsets from the newest main-series game with data.",
        },
        "types": types,
        "type_chart": type_chart,
        "generations": generations,
        "pseudo_legendaries": PSEUDO_LEGENDARIES,
        "pokemon": pokemon,
        "moves": moves,
        "items": items,
        "abilities": abilities,
    }


def build_megas(mega_rows, species_slug, items, item_rows, stats, pokemon_types, pokemon_abilities, ev_yield):
    """Per species slug: its Mega/Primal forms with stats, types and the item that triggers them."""
    form_names = {}  # pokemon id -> English name like "Mega Charizard X"
    form_pokemon = {r["id"]: r["pokemon_id"] for r in read("pokemon_forms")}
    for r in read("pokemon_form_names"):
        if r["local_language_id"] == ENGLISH and r["pokemon_name"] and r["pokemon_form_id"] in form_pokemon:
            form_names[form_pokemon[r["pokemon_form_id"]]] = r["pokemon_name"]

    stones = [r["identifier"] for r in item_rows if r["category_id"] == MEGA_STONE_CATEGORY]

    def stone_for(form_slug, form_id, species):
        """Older stones name their Mega in the effect text; newer ones only share the name stem."""
        name = form_names.get(form_id)
        for stone in stones:
            effect = items.get(stone, {}).get("effect", "")
            if name and effect.endswith(f"into {name}."):
                return stone
        variant = re.search(r"-mega(-[xyz])?$", form_slug).group(1) or ""
        candidates = [s for s in stones if (re.search(r"-[xyz]$", s) or [""])[0] == variant
                      and not items.get(s, {}).get("effect")]
        stem = lambda s: re.sub(r"-[xyz]$", "", s)  # noqa: E731
        best = max(candidates, key=lambda s: difflib.SequenceMatcher(None, stem(s), species).ratio(), default=None)
        if best and difflib.SequenceMatcher(None, stem(best), species).ratio() >= 0.6:
            return best
        return None

    megas = defaultdict(list)
    for r in sorted(mega_rows, key=lambda r: int(r["id"])):
        species = species_slug[r["species_id"]]
        slug, pid = r["identifier"], r["id"]
        if slug.endswith("-primal"):
            kind, item = "primal", PRIMAL_ORBS.get(species)
        else:
            kind, item = "mega", None if species in STONELESS_MEGAS else stone_for(slug, pid, species)
        megas[species].append({
            "slug": slug,
            "id": int(pid),
            "name": form_names.get(pid, slug.replace("-", " ").title()),
            "kind": kind,
            "item": item,
            "move": STONELESS_MEGAS.get(species) if kind == "mega" else None,
            "types": pokemon_types[pid],
            "stats": stats[pid],
            "abilities": pokemon_abilities[pid],
            "ev_yield": ev_yield[pid],
            "height_m": int(r["height"]) / 10,
            "weight_kg": int(r["weight"]) / 10,
        })
    for forms in megas.values():
        # Same display name for gender variants (Mega Meowstic): add the variant from the slug
        names = [f["name"] for f in forms]
        for f in forms:
            if names.count(f["name"]) > 1:
                variant = f["slug"].split("-")[1]
                f["name"] += f" ({variant.title()})"
    return megas


def build_evolutions(species_slug, item_slug, items, move_slug, moves, type_slug):
    """Map evolved species id -> human-readable method, e.g. 'use a Thunder Stone'."""
    triggers = {r["id"]: r["identifier"] for r in read("evolution_triggers")}
    locations = english_names("location_names", "location_id")

    def name_of(slug_map, table, key):
        slug = slug_map.get(key)
        return table[slug]["name"] if slug in table else (slug or "").replace("-", " ").title()

    def describe(r):
        trigger = triggers.get(r["evolution_trigger_id"], "")
        parts = []
        if trigger == "level-up":
            parts.append(f"at level {r['minimum_level']}" if r["minimum_level"] else "on level up")
        elif trigger == "trade":
            parts.append("when traded")
        elif trigger == "use-item":
            parts.append(f"using {article(name_of(item_slug, items, r['trigger_item_id']))}")
        elif trigger in SPECIAL_TRIGGERS:
            if SPECIAL_TRIGGERS[trigger]:
                parts.append(SPECIAL_TRIGGERS[trigger])
        else:
            parts.append(f"via {trigger.replace('-', ' ')}")

        if r["held_item_id"]:
            parts.append(f"while holding {article(name_of(item_slug, items, r['held_item_id']))}")
        if r["trade_species_id"]:
            parts.append(f"for {article(species_slug[r['trade_species_id']].title())}")
        if r["minimum_happiness"]:
            parts.append("with high friendship")
        if r["minimum_affection"]:
            parts.append("with high affection")
        if r["minimum_beauty"]:
            parts.append("with high Beauty")
        if r["known_move_id"]:
            parts.append(f"while knowing {name_of(move_slug, moves, r['known_move_id'])}")
        if r["known_move_type_id"]:
            parts.append(f"while knowing {article(type_slug[r['known_move_type_id']].title())}-type move")
        if r["location_id"]:
            parts.append(f"at {locations.get(r['location_id'], 'a special location')}")
        if r["time_of_day"]:
            parts.append(f"during the {r['time_of_day']}")
        if r["gender_id"]:
            parts.append("(female only)" if r["gender_id"] == "1" else "(male only)")
        if r["party_species_id"]:
            parts.append(f"with {species_slug[r['party_species_id']].title()} in the party")
        if r["party_type_id"]:
            parts.append(f"with {article(type_slug[r['party_type_id']].title())}-type in the party")
        if r["relative_physical_stats"]:
            rel = {"1": "Attack > Defense", "-1": "Attack < Defense", "0": "Attack = Defense"}
            parts.append(f"when {rel[r['relative_physical_stats']]}")
        if r["used_move_id"]:
            times = f" {r['minimum_move_count']} times" if r["minimum_move_count"] else ""
            parts.append(f"after using {name_of(move_slug, moves, r['used_move_id'])}{times}")
        if r["minimum_steps"]:
            parts.append(f"after walking {r['minimum_steps']} steps")
        if r["minimum_damage_taken"]:
            parts.append(f"after taking {r['minimum_damage_taken']} damage")
        if r["needs_multiplayer"] == "1":
            parts.append("in Union Circle")
        if r["needs_overworld_rain"] == "1":
            parts.append("while it is raining")
        if r["turn_upside_down"] == "1":
            parts.append("with the console held upside down")
        return " ".join(parts)

    def is_regional(r):
        # Default forms have ids below 10000; a row that starts from a higher form id
        # evolves an alternate form (Alolan Vulpix, Galarian Mr. Mime, Spewpa patterns)
        return bool(r["region_id"]) or int(r["required_pokemon_form_id"] or 0) >= 10000

    rows_by_species = defaultdict(list)
    for r in read("pokemon_evolution"):
        rows_by_species[r["evolved_species_id"]].append(r)

    methods = {}
    for species_id, rows in rows_by_species.items():
        # Prefer default-form rows (e.g. Raichu from Pikachu, not Alolan Raichu), then default
        # rows, then the newest game. Species that only evolve from a regional form
        # (e.g. Perrserker from Galarian Meowth) fall back to that row.
        rows.sort(
            key=lambda r: (not is_regional(r), r["is_default"] == "1", int(r["version_group_id"] or 0)),
            reverse=True,
        )
        methods[species_id] = describe(rows[0]) + (" (regional form only)" if is_regional(rows[0]) else "")
    return methods


def build_learnsets(pokemon_species_id, species_slug, move_slug, group_slug, group_order, group_names):
    """Per species: level-up and TM moves from the preferred (or newest) game with data."""
    by_pokemon = defaultdict(lambda: defaultdict(list))
    for r in read("pokemon_moves"):
        if r["pokemon_id"] not in pokemon_species_id or r["move_id"] not in move_slug:
            continue
        group = group_slug[r["version_group_id"]]
        if group in SKIPPED_LEARNSET_GROUPS:
            continue
        by_pokemon[r["pokemon_id"]][group].append(r)

    learnsets = {}
    for pokemon_id, groups in by_pokemon.items():
        if PREFERRED_LEARNSET_GROUP in groups:
            group = PREFERRED_LEARNSET_GROUP
        else:
            group = max(groups, key=lambda g: group_order[g])
        level, machine, egg = {}, set(), set()
        for r in groups[group]:
            move = move_slug[r["move_id"]]
            if r["pokemon_move_method_id"] == "1":  # level-up
                lvl = int(r["level"] or 0)
                level[move] = min(lvl, level.get(move, lvl))
            elif r["pokemon_move_method_id"] == "2":  # egg move
                egg.add(move)
            elif r["pokemon_move_method_id"] == "4":  # TM / machine
                machine.add(move)
        learnsets[species_slug[pokemon_species_id[pokemon_id]]] = {
            "game": " / ".join(group_names[group]),
            "level_up": sorted(([lvl, m] for m, lvl in level.items()), key=lambda x: (x[0], x[1])),
            "machine": sorted(machine),
            "egg": sorted(egg),
        }
    return learnsets


def main():
    parser = argparse.ArgumentParser(description="Build chatbot/data/pokedex.json from PokeAPI CSVs")
    parser.add_argument("--refresh", action="store_true", help="re-download all CSV files")
    args = parser.parse_args()

    download(args.refresh)
    data = build()
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)}: {len(data['pokemon'])} Pokemon, "
        f"{len(data['moves'])} moves, {len(data['items'])} items, {len(data['types'])} types"
    )


if __name__ == "__main__":
    sys.exit(main())
