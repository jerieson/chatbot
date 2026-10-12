import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.dex_api import create_router
from chatbot.pokedex import Pokedex


@pytest.fixture(scope="module")
def dex():
    return Pokedex()


@pytest.fixture(scope="module")
def client(dex):
    app = FastAPI()
    app.include_router(create_router(dex))
    return TestClient(app)


# ---- Search ------------------------------------------------------------------

def test_search_ranks_exact_then_prefix(dex):
    assert dex.search("gengar")[0] == ("pokemon", "gengar")
    assert dex.search("char")[:3] == [("pokemon", "charmander"), ("pokemon", "charmeleon"), ("pokemon", "charizard")]


def test_search_finds_moves_items_and_numbers(dex):
    assert ("moves", "thunderbolt") in dex.search("thunderbolt")
    assert dex.search("master ball")[0] == ("items", "master-ball")
    assert dex.search("#94") == [("pokemon", "gengar")]
    assert dex.search("9999") == []


def test_search_tolerates_typos(dex):
    assert ("pokemon", "gengar") in dex.search("gengr")


def test_search_endpoint(client):
    results = client.get("/dex/search", params={"q": "pika"}).json()["results"]
    assert results[0] == {"kind": "pokemon", "slug": "pikachu", "name": "Pikachu", "id": 25, "types": ["electric"]}


# ---- Pages -------------------------------------------------------------------

def test_pokemon_page(client):
    data = client.get("/dex/pokemon/gengar").json()
    assert data["name"] == "Gengar" and data["types"] == ["ghost", "poison"]
    assert data["stat_total"] == 500
    assert data["type_defenses"]["normal"] == 0 and data["type_defenses"]["ghost"] == 2
    assert data["evolution"]["slug"] == "gastly"
    assert data["evolution"]["evolves_to"][0]["evolves_to"][0]["slug"] == "gengar"
    assert data["previous"]["slug"] == "haunter" and data["next"]["slug"] == "onix"
    assert any(a["name"] == "Cursed Body" for a in data["abilities"])
    assert data["moves"]["level_up"] and "learnset" not in data


def test_move_page_lists_learners(client):
    data = client.get("/dex/move/shadow-ball").json()
    assert data["type"] == "ghost"
    assert any(p["slug"] == "gengar" for p in data["learned_by"])


def test_item_page_and_404s(client):
    assert client.get("/dex/item/master-ball").json()["name"] == "Master Ball"
    assert client.get("/dex/pokemon/missingno").status_code == 404
    assert client.get("/dex/move/nope").status_code == 404


def test_pokemon_page_includes_mega_forms(client):
    megas = client.get("/dex/pokemon/charizard").json()["forms"]
    assert [m["name"] for m in megas] == ["Mega Charizard X", "Mega Charizard Y"]
    x = megas[0]
    assert x["types"] == ["fire", "dragon"] and x["item"] == {"slug": "charizardite-x", "name": "Charizardite X"}
    assert x["stat_total"] == 634 and x["type_defenses"]["dragon"] == 2
    assert x["moves"] is None  # Megas keep the base learnset
    assert client.get("/dex/pokemon/rayquaza").json()["forms"][0]["move"]["name"] == "Dragon Ascent"
    assert client.get("/dex/pokemon/pikachu").json()["forms"] == []


def test_pokemon_page_includes_regional_forms(client):
    forms = client.get("/dex/pokemon/raichu").json()["forms"]
    alolan = forms[0]
    assert alolan["name"] == "Alolan Raichu" and alolan["kind"] == "regional" and alolan["region"] == "Alola"
    assert alolan["types"] == ["electric", "psychic"] and alolan["item"] is None
    assert any(m["type"] == "psychic" for m in alolan["moves"]["level_up"])
    assert [f["kind"] for f in forms] == ["regional", "mega", "mega"]
    tauros = [f["name"] for f in client.get("/dex/pokemon/tauros").json()["forms"]]
    assert tauros == ["Paldean Tauros (Combat Breed)", "Paldean Tauros (Blaze Breed)", "Paldean Tauros (Aqua Breed)"]
    names = [f["name"] for f in client.get("/dex/pokemon/darmanitan").json()["forms"]]
    assert names == ["Galarian Darmanitan"]  # Zen Mode is a battle form, not a regional form


def test_mega_stone_page_links_its_form(client):
    forms = client.get("/dex/item/gengarite").json()["mega_forms"]
    assert forms == [{"slug": "gengar-mega", "name": "Mega Gengar", "id": 10038, "types": ["ghost", "poison"],
                      "species": "gengar", "species_name": "Gengar", "species_id": 94}]
    assert client.get("/dex/item/red-orb").json()["mega_forms"][0]["slug"] == "groudon-primal"


def test_search_finds_regional_forms(client):
    result = client.get("/dex/search", params={"q": "alolan vulpix"}).json()["results"][0]
    assert result["slug"] == "vulpix" and result["form"] == "vulpix-alola" and result["types"] == ["ice"]


def test_search_finds_mega_forms(client):
    results = client.get("/dex/search", params={"q": "mega gengar"}).json()["results"]
    assert results[0] == {"kind": "pokemon", "slug": "gengar", "form": "gengar-mega", "name": "Mega Gengar",
                          "id": 10038, "types": ["ghost", "poison"]}
