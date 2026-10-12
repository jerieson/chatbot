# chatbot/answers.py - Build factual answers from Pokedex data for each intent

import re
from typing import Callable, Dict, List, Optional

from .pokedex import Entities, Pokedex

STAT_LABELS = [("hp", "HP"), ("attack", "Atk"), ("defense", "Def"),
               ("sp_attack", "SpA"), ("sp_defense", "SpD"), ("speed", "Spe")]
# Questions the data can't answer well (opinions, locations, lore) go to the LLM instead
OPEN_ENDED_INTENTS = {"legendary", "starter", "region"}
OPEN_ENDED_RE = re.compile(
    r"\b(best|strongest|weakest|good|better|should|recommend|where|gym|leader|city|cities|"
    r"league|elite|lore|story)\b"
)


def type_name(slug: str) -> str:
    return slug.title()


def join(names: List[str]) -> str:
    if not names:
        return "nothing"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def article(word: str) -> str:
    return f"an {word}" if word[:1].lower() in "aeiou" else f"a {word}"


def multiplier(factor: float) -> str:
    return f"{factor:g}x"


class AnswerBuilder:
    def __init__(self, pokedex: Pokedex):
        self.dex = pokedex
        self.handlers: Dict[str, Callable[[str, Entities], Optional[str]]] = {
            "pokemon_info": self.pokemon_info,
            "legendary": self.legendary,
            "pseudo_legendary": self.pseudo_legendary,
            "starter": self.starter,
            "pokemon_type": self.pokemon_type,
            "type_weakness": self.type_weakness,
            "type_resistance": self.type_resistance,
            "type_immunity": self.type_immunity,
            "evolution": self.evolution,
            "evolution_item": self.evolution_item,
            "pre_evolution": self.pre_evolution,
            "move_info": self.move_info,
            "move_type": self.move_type,
            "move_learn": self.move_learn,
            "item_info": self.item_info,
            "region": self.region,
            "compare": self.compare,
        }

    def answer(self, intent: str, message: str, entities: Entities,
               allow_open_ended: bool = False) -> Optional[str]:
        """Return a data-backed answer, or None if this intent/entity combination isn't covered.

        Opinion questions ("Which starter is best?") return None so an LLM can answer them,
        unless allow_open_ended is set (used when no LLM is available).
        """
        handler = self.handlers.get(intent)
        if handler is None:
            return None
        if (not allow_open_ended and intent in OPEN_ENDED_INTENTS and not entities.pokemon
                and OPEN_ENDED_RE.search(message.lower())):
            return None
        return handler(message.lower(), entities)

    # ---- Pokemon profiles ----------------------------------------------------

    def name(self, slug: str) -> str:
        return self.dex.pokemon[slug]["name"]

    def types_of(self, slug: str) -> str:
        return "/".join(type_name(t) for t in self.dex.pokemon[slug]["types"])

    def stat_line(self, slug: str) -> str:
        stats = self.dex.pokemon[slug]["stats"]
        parts = [f"{label} {stats[key]}" for key, label in STAT_LABELS]
        return " / ".join(parts) + f" (total {sum(stats.values())})"

    def status_notes(self, slug: str) -> List[str]:
        p = self.dex.pokemon[slug]
        notes = []
        if p["legendary"]:
            notes.append("a Legendary Pokémon")
        if p["mythical"]:
            notes.append("a Mythical Pokémon")
        if self.dex.is_pseudo_legendary(slug):
            notes.append("a pseudo-legendary")
        if slug in self.dex.starters:
            notes.append(f"a starter Pokémon in {self.dex.generations[p['generation']]['region']}")
        if p["baby"]:
            notes.append("a baby Pokémon")
        return notes

    def profile(self, slug: str) -> str:
        p = self.dex.pokemon[slug]
        region = self.dex.generations[p["generation"]]["region"]
        lines = [f"{p['name']}, the {p['genus']}: {article(self.types_of(slug))}-type Pokémon "
                 f"introduced in Generation {p['generation']} ({region})."]
        notes = self.status_notes(slug)
        if notes:
            lines.append(f"It is {join(notes)}.")
        family = self.dex.evolution_lines(slug)
        if family != [p["name"]]:
            lines.append("Evolution: " + "; ".join(family))
        else:
            lines.append("It does not evolve.")
        lines.append(f"Base stats: {self.stat_line(slug)}")
        if p["flavor_text"]:
            lines.append(f"Pokédex: {p['flavor_text']}")
        return "\n".join(lines)

    def pokemon_info(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon:
            return "\n\n".join(self.profile(s) for s in e.pokemon[:2])
        if e.moves:
            return self.move_info(message, e)
        if e.items:
            return self.item_info(message, e)
        return None

    def legendary(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon:
            slug = e.pokemon[0]
            p = self.dex.pokemon[slug]
            if p["legendary"] or p["mythical"]:
                verdict = f"Yes, {p['name']} is {'a Legendary' if p['legendary'] else 'a Mythical'} Pokémon."
            else:
                verdict = f"No, {p['name']} is not a Legendary or Mythical Pokémon."
            return f"{verdict}\n\n{self.profile(slug)}"
        gens = e.generations
        if not gens:
            counts = [f"Gen {g}: {len(self._legends(g))}" for g in self.dex.generations]
            return ("Legendary and Mythical Pokémon per generation: " + ", ".join(counts)
                    + ". Ask about a specific region (e.g. \"legendaries in Kanto\") to see them.")
        lines = []
        for g in gens:
            legends = self._legends(g)
            region = self.dex.generations[g]["region"]
            lines.append(f"Generation {g} ({region}): " + join(
                [self.name(s) + (" (Mythical)" if self.dex.pokemon[s]["mythical"] else "") for s in legends]))
        return "\n".join(lines)

    def _legends(self, gen: int) -> List[str]:
        return [s for s, p in sorted(self.dex.pokemon.items(), key=lambda kv: kv[1]["id"])
                if p["generation"] == gen and (p["legendary"] or p["mythical"])]

    def pseudo_legendary(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon:
            slug = e.pokemon[0]
            if self.dex.is_pseudo_legendary(slug):
                verdict = f"Yes, {self.name(slug)} is a pseudo-legendary (base stat total 600)."
            else:
                # Pre-evolutions count as part of the family: "Is Dratini pseudo-legendary?"
                line = next((chain for chain in self.dex.evolution_lines(slug)
                             if any(self.name(p) in chain for p in self.dex.pseudo_legendaries)), None)
                verdict = (f"{self.name(slug)} is in a pseudo-legendary family: {line}" if line
                           else f"No, {self.name(slug)} is not a pseudo-legendary.")
            return f"{verdict}\n\n{self.profile(slug)}"
        pseudos = [s for s in self.dex.pseudo_legendaries
                   if not e.generations or self.dex.pokemon[s]["generation"] in e.generations]
        if not pseudos:
            return f"There is no pseudo-legendary from Generation {join([str(g) for g in e.generations])}."
        names = [f"{self.name(s)} (Gen {self.dex.pokemon[s]['generation']})" for s in pseudos]
        return ("Pseudo-legendaries are three-stage Pokémon with a base stat total of 600: "
                + join(names) + ".")

    def starter(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon:
            return self.pokemon_info(message, e)
        gens = e.generations or list(self.dex.generations)
        lines = []
        for g in gens:
            info = self.dex.generations[g]
            starters = [s for s in info["starters"]
                        if not e.types or set(e.types) & set(self.dex.pokemon[s]["types"])]
            if starters:
                lines.append(f"{info['region']} (Gen {g}): "
                             + join([f"{self.name(s)} ({self.types_of(s)})" for s in starters]))
        return "\n".join(lines) if lines else None

    # ---- Types ---------------------------------------------------------------

    def pokemon_type(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon:
            return "\n".join(f"{self.name(s)} is {article(self.types_of(s))}-type Pokémon." for s in e.pokemon)
        if e.moves:
            return "\n".join(f"{self.dex.moves[m]['name']} is {article(type_name(self.dex.moves[m]['type']))}-type move."
                             for m in e.moves)
        return None

    def _defender(self, e: Entities):
        """(label, types) for the defending side of a matchup question."""
        if e.pokemon:
            slug = e.pokemon[0]
            return f"{self.name(slug)} ({self.types_of(slug)})", self.dex.pokemon[slug]["types"]
        if e.types:
            types = e.types[:2]
            return "/".join(type_name(t) for t in types) + " type", types
        return None, None

    def type_weakness(self, message: str, e: Entities) -> Optional[str]:
        label, types = self._defender(e)
        if not types:
            return None
        profile = self.dex.defensive_profile(types)
        weak = [f"{join([type_name(t) for t in profile[f]])} ({multiplier(f)})"
                for f in sorted(profile, reverse=True) if f > 1]
        lines = [f"{label} is weak to: {join(weak) if weak else 'no types'}."]
        if not e.pokemon and len(types) == 1:
            strong = self.dex.offensive_profile(types[0]).get(2.0, [])
            lines.append(f"{type_name(types[0])} attacks are super effective against: "
                         f"{join([type_name(t) for t in strong])}.")
        return "\n".join(lines)

    def type_resistance(self, message: str, e: Entities) -> Optional[str]:
        label, types = self._defender(e)
        if not types:
            return None
        profile = self.dex.defensive_profile(types)
        resists = [f"{join([type_name(t) for t in profile[f]])} ({multiplier(f)})"
                   for f in sorted(profile) if 0 < f < 1]
        lines = [f"{label} resists: {join(resists) if resists else 'no types'}."]
        if profile.get(0.0):
            lines.append(f"It is immune to: {join([type_name(t) for t in profile[0.0]])}.")
        return "\n".join(lines)

    def type_immunity(self, message: str, e: Entities) -> Optional[str]:
        # "What is immune to Fighting?" asks about the attacking type
        attack = re.search(r"immune to (\w+)", message)
        if attack and attack.group(1) in self.dex.types and not e.pokemon:
            attacker = attack.group(1)
            immune = self.dex.offensive_profile(attacker).get(0.0, [])
            if not immune:
                return f"No type is immune to {type_name(attacker)}-type moves."
            return (f"{join([type_name(t) for t in immune])} "
                    f"{'is' if len(immune) == 1 else 'are'} immune to {type_name(attacker)}-type moves.")
        label, types = self._defender(e)
        if types:
            immune = self.dex.defensive_profile(types).get(0.0, [])
            if not immune:
                return f"{label} has no type immunities."
            return f"{label} is immune to {join([type_name(t) for t in immune])}-type moves."
        pairs = [f"{type_name(d)} is immune to {type_name(a)}"
                 for a, row in self.dex.type_chart.items() for d, f in row.items() if f == 0]
        return "Type immunities: " + "; ".join(pairs) + "."

    # ---- Evolution -----------------------------------------------------------

    def evolution(self, message: str, e: Entities) -> Optional[str]:
        if not e.pokemon:
            return self.evolution_item(message, e) if e.items else None
        if len(e.pokemon) >= 2:
            # "How do I evolve Eevee into Umbreon?": describe just that path
            a, b = e.pokemon[:2]
            path = self.dex.evolution_path(a, b) or self.dex.evolution_path(b, a)
            if path:
                return "\n".join(f"{self.name(x)} evolves into {self.name(y)} "
                                 f"{self.dex.pokemon[y]['evolution_method']}." for x, y in zip(path, path[1:]))
        answers, roots = [], set()
        for slug in e.pokemon[:2]:
            root = self.dex.chain_root(slug)
            if root in roots:
                continue  # same family already shown
            roots.add(root)
            family = self.dex.evolution_lines(slug)
            if family == [self.name(slug)]:
                answers.append(f"{self.name(slug)} does not evolve.")
            else:
                answers.append(f"{self.name(slug)}'s evolution family:\n" + "\n".join(family))
        return "\n\n".join(answers)

    def evolution_item(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon:
            slug = e.pokemon[0]
            kids = self.dex.children.get(slug, [])
            if not kids:
                return self.pre_evolution(message, e) if self.dex.pokemon[slug]["evolves_from"] \
                    else f"{self.name(slug)} does not evolve."
            return "\n".join(f"{self.name(slug)} evolves into {self.name(k)} "
                             f"{self.dex.pokemon[k]['evolution_method']}." for k in kids)
        if e.items:
            item = self.dex.items[e.items[0]]["name"]
            users = [s for s, p in sorted(self.dex.pokemon.items(), key=lambda kv: kv[1]["id"])
                     if item in (p["evolution_method"] or "")]
            if not users:
                return f"No Pokémon evolves using {article(item)}."
            return f"Pokémon that evolve with {article(item)}:\n" + "\n".join(
                f"{self.name(self.dex.pokemon[s]['evolves_from'])} -> {self.name(s)}" for s in users)
        return None

    def pre_evolution(self, message: str, e: Entities) -> Optional[str]:
        if not e.pokemon:
            return None
        lines = []
        for slug in e.pokemon[:2]:
            p = self.dex.pokemon[slug]
            if p["evolves_from"]:
                lines.append(f"{p['name']} evolves from {self.name(p['evolves_from'])} "
                             f"{p['evolution_method'] or ''}".rstrip() + ".")
            else:
                kids = self.dex.children.get(slug, [])
                tail = f" It is the first stage of its family and evolves into {join([self.name(k) for k in kids])}." \
                    if kids else ""
                lines.append(f"{p['name']} does not evolve from any Pokémon.{tail}")
        return "\n".join(lines)

    # ---- Moves -----------------------------------------------------------------

    def move_summary(self, slug: str) -> str:
        m = self.dex.moves[slug]
        stats = [f"Power {m['power'] or '-'}", f"Accuracy {str(m['accuracy']) + '%' if m['accuracy'] else '-'}",
                 f"PP {m['pp']}"]
        if m["priority"]:
            stats.append(f"Priority {m['priority']:+d}")
        text = f"{m['name']}: {type_name(m['type'])}-type {m['damage_class']} move. {', '.join(stats)}."
        return text + (f" Effect: {m['effect']}" if m["effect"] else "")

    def move_info(self, message: str, e: Entities) -> Optional[str]:
        if not e.moves:
            return None
        return "\n".join(self.move_summary(m) for m in e.moves[:3])

    def move_type(self, message: str, e: Entities) -> Optional[str]:
        if e.types:
            t = e.types[0]
            of_type = [m for m in self.dex.moves.values() if m["type"] == t]
            strongest = sorted((m for m in of_type if m["power"]), key=lambda m: -m["power"])[:10]
            return (f"There are {len(of_type)} {type_name(t)}-type moves. The most powerful: "
                    + join([f"{m['name']} ({m['power']})" for m in strongest]) + ".")
        if e.moves:
            return self.pokemon_type(message, Entities(moves=e.moves))
        return None

    def move_learn(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon and e.moves:
            return "\n".join(self._learns(p, m) for p in e.pokemon[:2] for m in e.moves[:2])
        if e.pokemon:
            slug = e.pokemon[0]
            learnset = self.dex.pokemon[slug]["learnset"]
            if not learnset:
                return f"I don't have move data for {self.name(slug)}."
            level_up = [f"{'Evolve' if lvl == 0 else f'Lv {lvl}'} {self.dex.moves[m]['name']}"
                        for lvl, m in learnset["level_up"]]
            return (f"{self.name(slug)} learns by level up ({learnset['game']}): {', '.join(level_up)}.\n"
                    f"It can also learn {len(learnset['machine'])} moves by TM.")
        if e.moves:
            move = e.moves[0]
            learners = [s for s, p in self.dex.pokemon.items()
                        if p["learnset"] and (move in p["learnset"]["machine"]
                                              or any(m == move for _, m in p["learnset"]["level_up"]))]
            sample = join([self.name(s) for s in learners[:10]])
            return f"{len(learners)} Pokémon can learn {self.dex.moves[move]['name']}, including {sample}."
        return None

    def _learns(self, slug: str, move: str) -> str:
        p, m = self.dex.pokemon[slug], self.dex.moves[move]
        learnset = p["learnset"]
        if not learnset:
            return f"I don't have move data for {p['name']}."
        levels = [lvl for lvl, mv in learnset["level_up"] if mv == move]
        ways = []
        if levels:
            ways.append({0: "on evolution", 1: "at level 1"}.get(levels[0], f"at level {levels[0]}"))
        if move in learnset["machine"]:
            ways.append("by TM")
        if not ways:
            return f"{p['name']} can't learn {m['name']} in {learnset['game']} (by level up or TM)."
        return f"{p['name']} learns {m['name']} {' and '.join(ways)} in {learnset['game']}."

    # ---- Items, regions, comparisons -------------------------------------------

    def item_info(self, message: str, e: Entities) -> Optional[str]:
        if not e.items:
            return None
        lines = []
        for slug in e.items[:3]:
            item = self.dex.items[slug]
            text = f"{item['name']} ({item['category']}): {item['effect'] or 'No description available.'}"
            if item["cost"]:
                text += f" Costs {item['cost']} Pokédollars."
            lines.append(text)
        return "\n".join(lines)

    def region(self, message: str, e: Entities) -> Optional[str]:
        if e.pokemon and not e.generations:
            return "\n".join(
                f"{self.name(s)} was introduced in Generation {self.dex.pokemon[s]['generation']} "
                f"({self.dex.generations[self.dex.pokemon[s]['generation']]['region']})." for s in e.pokemon)
        if not e.generations:
            return "The main-series regions are: " + join(
                [f"{g['region']} (Gen {n})" for n, g in self.dex.generations.items()]) + "."
        lines = []
        for gen in e.generations:
            info = self.dex.generations[gen]
            legends = self._legends(gen)
            lines.append(
                f"{info['region']} is the Generation {gen} region, introduced in {join(info['games'])}. "
                f"It introduced {info['pokemon_count']} new Pokémon. "
                f"Starters: {join([self.name(s) for s in info['starters']])}. "
                f"Legendary/Mythical Pokémon: {join([self.name(s) for s in legends])}."
            )
        return "\n".join(lines)

    def compare(self, message: str, e: Entities) -> Optional[str]:
        if len(e.pokemon) < 2:
            return None
        a, b = e.pokemon[:2]
        pa, pb = self.dex.pokemon[a], self.dex.pokemon[b]
        lines = [f"{pa['name']} ({self.types_of(a)}) vs {pb['name']} ({self.types_of(b)})"]
        for key, label in STAT_LABELS:
            lines.append(f"{label}: {pa['stats'][key]} vs {pb['stats'][key]}")
        total_a, total_b = sum(pa["stats"].values()), sum(pb["stats"].values())
        lines.append(f"Total: {total_a} vs {total_b}")
        if total_a != total_b:
            lines.append(f"{(pa if total_a > total_b else pb)['name']} has the higher base stat total.")
        if pa["stats"]["speed"] != pb["stats"]["speed"]:
            faster = pa if pa["stats"]["speed"] > pb["stats"]["speed"] else pb
            lines.append(f"{faster['name']} is faster.")
        for attacker, defender in ((pa, pb), (pb, pa)):
            best = max(self.dex.effectiveness(t, defender["types"]) for t in attacker["types"])
            lines.append(f"{attacker['name']}'s own-type moves hit {defender['name']} for up to {multiplier(best)}.")
        return "\n".join(lines)

    def best_guess(self, e: Entities) -> Optional[str]:
        """When the question is unclear, describe the most specific thing it mentions."""
        if e.pokemon:
            return self.profile(e.pokemon[0])
        if e.moves:
            return self.move_summary(e.moves[0])
        if e.items:
            return self.item_info("", Entities(items=e.items[:1]))
        if e.types:
            return self.type_weakness("", Entities(types=e.types[:1]))
        if e.generations:
            return self.region("", Entities(generations=e.generations[:1]))
        return None

    # ---- Context for the LLM fallback --------------------------------------------

    def facts(self, e: Entities) -> str:
        """Compact reference data about the mentioned entities, for grounding LLM answers."""
        parts = [self.profile(s) for s in e.pokemon[:3]]
        parts += [self.move_summary(m) for m in e.moves[:3]]
        parts += [self.item_info("", Entities(items=[i])) for i in e.items[:3]]
        for t in e.types[:2]:
            parts.append(self.type_weakness("", Entities(types=[t])))
        for g in e.generations[:1]:
            parts.append(self.region("", Entities(generations=[g])))
        return "\n\n".join(p for p in parts if p)
