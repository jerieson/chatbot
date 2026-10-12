# backend/dex_api.py - Pokedex browser endpoints: search, plus one Pokemon / move / item page

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from chatbot.pokedex import Pokedex


def create_router(pokedex: Pokedex) -> APIRouter:
    router = APIRouter(prefix="/dex", tags=["pokedex"])

    def pokemon_summary(slug: str) -> Dict:
        p = pokedex.pokemon[slug]
        return {"slug": slug, "name": p["name"], "id": p["id"], "types": p["types"]}

    def move_row(slug: str, **extra) -> Optional[Dict]:
        m = pokedex.moves.get(slug)
        if m is None:
            return None
        return {"slug": slug, "name": m["name"], "type": m["type"], "damage_class": m["damage_class"],
                "power": m["power"], "accuracy": m["accuracy"], **extra}

    def evolution_tree(slug: str) -> Dict:
        node = {**pokemon_summary(slug), "method": pokedex.pokemon[slug]["evolution_method"]}
        node["evolves_to"] = [evolution_tree(child) for child in pokedex.children.get(slug, [])]
        return node

    # Mega Stones / Primal orbs -> the forms they unlock, for item pages
    forms_by_item: Dict[str, List[Dict]] = {}
    for species_slug, p in pokedex.pokemon.items():
        for form in p.get("megas", []):
            if form["item"]:
                forms_by_item.setdefault(form["item"], []).append(
                    {"slug": form["slug"], "name": form["name"], "id": form["id"], "types": form["types"],
                     "species": species_slug, "species_name": p["name"], "species_id": p["id"]})

    def expand_abilities(abilities: List[Dict]) -> List[Dict]:
        return [{"slug": a["ability"], "hidden": a["hidden"], **pokedex.abilities.get(a["ability"], {})}
                for a in abilities]

    def mega_form(form: Dict) -> Dict:
        item = pokedex.items.get(form["item"] or "")
        move = pokedex.moves.get(form["move"] or "")
        return {
            **form,
            "abilities": expand_abilities(form["abilities"]),
            "stat_total": sum(form["stats"].values()),
            "type_defenses": {t: pokedex.effectiveness(t, form["types"]) for t in pokedex.types},
            "item": {"slug": form["item"], "name": item["name"]} if item else None,
            "move": {"slug": form["move"], "name": move["name"]} if move else None,
        }

    @router.get("/search")
    async def search(q: str = Query(..., min_length=1, max_length=50), limit: int = Query(8, ge=1, le=20)):
        results = []
        for kind, slug in pokedex.search(q, limit):
            if kind == "pokemon":
                results.append({"kind": "pokemon", **pokemon_summary(slug)})
            elif kind == "forms":
                species, form = pokedex.forms[slug]
                results.append({"kind": "pokemon", "slug": species, "form": slug, "name": form["name"],
                                "id": form["id"], "types": form["types"]})
            elif kind == "moves":
                m = pokedex.moves[slug]
                results.append({"kind": "move", "slug": slug, "name": m["name"], "type": m["type"]})
            else:
                i = pokedex.items[slug]
                results.append({"kind": "item", "slug": slug, "name": i["name"], "category": i["category"]})
        return {"results": results}

    @router.get("/pokemon/{slug}")
    async def pokemon(slug: str):
        p = pokedex.pokemon.get(slug)
        if p is None:
            raise HTTPException(status_code=404, detail="Pokemon not found")

        learnset = p.get("learnset") or {}
        moves = {
            "game": learnset.get("game"),
            "level_up": [row for lvl, m in learnset.get("level_up", []) if (row := move_row(m, level=lvl))],
            "machine": [row for m in learnset.get("machine", []) if (row := move_row(m))],
            "egg": [row for m in learnset.get("egg", []) if (row := move_row(m))],
        }
        abilities = expand_abilities(p.get("abilities", []))
        neighbours = {
            "previous": pokemon_summary(pokedex.by_id[p["id"] - 1]) if p["id"] - 1 in pokedex.by_id else None,
            "next": pokemon_summary(pokedex.by_id[p["id"] + 1]) if p["id"] + 1 in pokedex.by_id else None,
        }
        return {
            **{k: v for k, v in p.items() if k not in ("learnset", "abilities", "megas")},
            "megas": [mega_form(f) for f in p.get("megas", [])],
            "slug": slug,
            "abilities": abilities,
            "stat_total": sum(p["stats"].values()),
            "type_defenses": {t: pokedex.effectiveness(t, p["types"]) for t in pokedex.types},
            "evolution": evolution_tree(pokedex.chain_root(slug)),
            "moves": moves,
            **neighbours,
        }

    @router.get("/move/{slug}")
    async def move(slug: str):
        m = pokedex.moves.get(slug)
        if m is None:
            raise HTTPException(status_code=404, detail="Move not found")

        learned_by: List[Dict] = []
        for pslug, p in sorted(pokedex.pokemon.items(), key=lambda kv: kv[1]["id"]):
            learnset = p.get("learnset") or {}
            levels = [lvl for lvl, name in learnset.get("level_up", []) if name == slug]
            how = [f"Lv. {levels[0]}" if levels[0] else "Lv. 1"] if levels else []
            if slug in learnset.get("machine", []):
                how.append("TM")
            if slug in learnset.get("egg", []):
                how.append("Egg")
            if how:
                learned_by.append({**pokemon_summary(pslug), "how": ", ".join(how)})
        return {**m, "slug": slug, "learned_by": learned_by}

    @router.get("/item/{slug}")
    async def item(slug: str):
        i = pokedex.items.get(slug)
        if i is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return {**i, "slug": slug, "mega_forms": forms_by_item.get(slug, [])}

    return router
