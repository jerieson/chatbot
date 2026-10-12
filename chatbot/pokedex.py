# chatbot/pokedex.py - Pokemon reference data and entity extraction
#
# Data comes from chatbot/data/pokedex.json, built by scripts/import_pokeapi.py.

import difflib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from shared import config

MAX_NAME_WORDS = 4
# Category words used by mask(); "psychic" is both a type and a move, and the type wins
MASK_PRIORITY = ["pokemon", "types", "generations", "moves", "items"]
MASK_LABELS = {"pokemon": "pokemon", "types": "type", "generations": "region", "moves": "move", "items": "item"}
# Move/item names that are everyday words; mask() leaves them alone ("how to counter fire types")
COMMON_WORDS = set("""
absorb acid assist attract barrier bind bite block bounce bubble camouflage celebrate charge charm
clamp coaching coil confide confusion constrict conversion counter covet curse cut decorate detect
dig disable discharge dive endeavor endure explosion facade feint flash flatter fling fly
frustration glare gravity growl growth grudge gust hail harden haze howl imprison infestation
instruct judgment lick lunge magnitude meditate memento mimic minimize mist moonlight nightmare
obstruct overdrive overheat payback peck pluck pounce pound powder present protect punishment purify
pursuit quash rage recover recycle reflect refresh rest retaliate return revenge reversal roar round
sharpen shelter sing sketch slam slash snarl snatch snore soak spark spikes spite splash spotlight
strength struggle submission substitute swagger swallow swift tackle taunt teatime teleport thief
thrash tickle torment toxic transform trick twister uproar whirlwind wish withdraw wrap yawn
apple avocado bacon banana basil bicycle bread butter calcium cheese chorizo cucumber egg ham honey
horseradish iron jalapeno jam journal ketchup kiwi lemonade letter lettuce lure magnet marble
marmalade mayonnaise mustard noodles nugget onion parcel pass pasta pearl pepper permit pickle
pineapple prosciutto protector protein rice ruby salt sandwich sapphire sausages scanner snowball
stick strawberry tea tofu tomato vinegar wasabi watercress yogurt zinc
""".split())
GENERATION_RE = re.compile(r"\bgen(?:eration)?\s*([1-9])\b")
# Words that look like typos of Pokemon names but are ordinary question words
FUZZY_STOPWORDS = {
    "starter", "starters", "stronger", "strongest", "pokemon", "evolve", "evolves", "evolution",
    "legendary", "legendaries", "region", "moves", "learn", "weakness", "resist", "immune",
    "between", "better", "compare", "where", "which", "items", "types", "stats", "about",
    "chatbot",
}


def normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation: "Farfetch'd" -> "farfetchd", "Mr. Mime" -> "mr mime"."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"['’]s\b", "", text)  # possessives: "Bulbasaur's" -> "Bulbasaur"
    text = re.sub(r"['’]", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


@dataclass
class Entities:
    pokemon: List[str] = field(default_factory=list)
    moves: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
    generations: List[int] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.pokemon or self.moves or self.items or self.types or self.generations)

    def merged_with(self, other: "Entities") -> "Entities":
        """Fill empty slots from `other` (used to carry context from earlier messages)."""
        return Entities(
            pokemon=self.pokemon or other.pokemon,
            moves=self.moves or other.moves,
            items=self.items or other.items,
            types=self.types or other.types,
            generations=self.generations or other.generations,
        )


class Pokedex:
    def __init__(self, path: Union[str, Path, None] = None):
        path = Path(path or config.POKEDEX_PATH)
        if not path.exists():
            raise FileNotFoundError(f"Pokedex not found: {path}. Run: python scripts/import_pokeapi.py")
        data = json.loads(path.read_text(encoding="utf-8"))

        self.pokemon: Dict[str, dict] = data["pokemon"]
        self.moves: Dict[str, dict] = data["moves"]
        self.items: Dict[str, dict] = data["items"]
        self.types: Dict[str, dict] = data["types"]
        self.type_chart: Dict[str, Dict[str, float]] = data["type_chart"]
        self.generations: Dict[int, dict] = {int(g): v for g, v in data["generations"].items()}
        self.pseudo_legendaries: List[str] = data["pseudo_legendaries"]

        self.starters = {s for g in self.generations.values() for s in g["starters"]}
        self.children: Dict[str, List[str]] = {}
        for slug, p in sorted(self.pokemon.items(), key=lambda kv: kv[1]["id"]):
            if p["evolves_from"]:
                self.children.setdefault(p["evolves_from"], []).append(slug)

        self._build_index()

    # ---- Entity extraction -------------------------------------------------

    def _build_index(self):
        self._index: Dict[str, List[tuple]] = {}

        def add(phrase: str, kind: str, slug):
            key = normalize(phrase)
            # Also index multi-word names without spaces: "Poke Ball" -> "pokeball"
            # The first entry wins when two share a name (e.g. a Legends: Arceus "Ultra Ball")
            for k in {key, key.replace(" ", "")}:
                if k and all(existing != kind for existing, _ in self._index.setdefault(k, [])):
                    self._index[k].append((kind, slug))

        for kind, table in (("pokemon", self.pokemon), ("moves", self.moves), ("items", self.items)):
            for slug, entry in table.items():
                add(entry["name"], kind, slug)
                add(slug.replace("-", " "), kind, slug)
        for slug in self.types:
            add(slug, "types", slug)
        for gen, info in self.generations.items():
            add(info["region"], "generations", gen)

        self._fuzzy_names = {normalize(p["name"]): slug for slug, p in self.pokemon.items()
                             if " " not in normalize(p["name"])}
        words_path = config.PROJECT_ROOT / "chatbot" / "data" / "english_words.txt"
        self._english_words = set()
        if words_path.exists():
            self._english_words = {line for line in words_path.read_text(encoding="utf-8").splitlines()
                                   if line and not line.startswith("#")}

    def _scan(self, tokens: List[str]) -> List[Tuple[int, int, List[tuple]]]:
        """Find name spans as (start, length, [(kind, slug), ...]), longest phrase first,
        so "Fire Blast" is a move rather than the Fire type."""
        spans = []
        unmatched = []
        i = 0
        while i < len(tokens):
            for n in range(min(MAX_NAME_WORDS, len(tokens) - i), 0, -1):
                phrase = " ".join(tokens[i:i + n])
                matches = self._index.get(phrase)
                if not matches and n == 1 and phrase.endswith("s"):
                    matches = self._index.get(phrase[:-1])  # plurals: "potions" -> "potion"
                if matches:
                    spans.append((i, n, matches))
                    i += n
                    break
            else:
                unmatched.append(i)
                i += 1

        # Tolerate typos in Pokemon names ("pikachoo"). Typos rarely change the first letters,
        # so require those to match ("hello" must not become Shellos).
        for i in unmatched:
            token = tokens[i]
            if len(token) < 5 or token in FUZZY_STOPWORDS or token in self._english_words:
                continue
            candidates = [n for n in self._fuzzy_names if n[:2] == token[:2]]
            close = difflib.get_close_matches(token, candidates, n=1, cutoff=0.8)
            if close:
                spans.append((i, 1, [("pokemon", self._fuzzy_names[close[0]])]))
        return sorted(spans)

    def extract(self, text: str) -> Entities:
        """Find Pokemon, moves, items, types and regions/generations mentioned in text."""
        entities = Entities()
        normalized = normalize(text)
        for _, _, matches in self._scan(normalized.split()):
            for kind, slug in matches:
                bucket = getattr(entities, kind)
                if slug not in bucket:
                    bucket.append(slug)

        for m in GENERATION_RE.finditer(normalized):
            gen = int(m.group(1))
            if gen in self.generations and gen not in entities.generations:
                entities.generations.append(gen)
        return entities

    def mask(self, text: str) -> str:
        """Replace names with their category for the intent classifier:
        "What type is Garchomp?" -> "what type is pokemon".

        The classifier then learns question shapes instead of memorizing names. Names that are
        everyday words ("counter", "rest") stay as they are.
        """
        tokens = normalize(text).split()
        out, i = [], 0
        for start, n, matches in self._scan(tokens):
            out.extend(tokens[i:start])
            phrase = " ".join(tokens[start:start + n])
            kinds = {kind for kind, _ in matches if not (kind in ("moves", "items") and phrase in COMMON_WORDS)}
            label = next((MASK_LABELS[k] for k in MASK_PRIORITY if k in kinds), None)
            out.extend([label] if label else tokens[start:start + n])
            i = start + n
        out.extend(tokens[i:])
        return " ".join(out)

    # ---- Type matchups -----------------------------------------------------

    def effectiveness(self, attack_type: str, defender_types: List[str]) -> float:
        factor = 1.0
        for t in defender_types:
            factor *= self.type_chart.get(attack_type, {}).get(t, 1.0)
        return factor

    def defensive_profile(self, defender_types: List[str]) -> Dict[float, List[str]]:
        """Group attacking types by damage multiplier against the given defending types."""
        profile: Dict[float, List[str]] = {}
        for attack_type in self.types:
            profile.setdefault(self.effectiveness(attack_type, defender_types), []).append(attack_type)
        return profile

    def offensive_profile(self, attack_type: str) -> Dict[float, List[str]]:
        profile: Dict[float, List[str]] = {}
        for defender in self.types:
            profile.setdefault(self.effectiveness(attack_type, [defender]), []).append(defender)
        return profile

    # ---- Evolution ---------------------------------------------------------

    def chain_root(self, slug: str) -> str:
        while self.pokemon[slug]["evolves_from"]:
            slug = self.pokemon[slug]["evolves_from"]
        return slug

    def evolution_path(self, start: str, end: str) -> Optional[List[str]]:
        """Slugs from `start` down to its descendant `end`, e.g. eevee -> umbreon; None if unrelated."""
        path = [end]
        while path[-1] != start:
            parent = self.pokemon[path[-1]]["evolves_from"]
            if parent is None:
                return None
            path.append(parent)
        return path[::-1]

    def evolution_lines(self, slug: str) -> List[str]:
        """Each branch of the family as text, e.g. ["Charmander -> Charmeleon (at level 16) -> ..."]."""
        lines: List[str] = []

        def walk(current: str, prefix: str):
            kids = self.children.get(current, [])
            if not kids:
                lines.append(prefix)
                return
            for kid in kids:
                method = self.pokemon[kid]["evolution_method"]
                step = f"{self.pokemon[kid]['name']} ({method})" if method else self.pokemon[kid]["name"]
                walk(kid, f"{prefix} -> {step}")

        root = self.chain_root(slug)
        walk(root, self.pokemon[root]["name"])
        return lines

    # ---- Misc helpers ------------------------------------------------------

    def is_pseudo_legendary(self, slug: str) -> bool:
        return slug in self.pseudo_legendaries

    def generation_of_region(self, gen: int) -> Optional[dict]:
        return self.generations.get(gen)
