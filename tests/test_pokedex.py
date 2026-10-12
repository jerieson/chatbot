import pytest

from chatbot.answers import AnswerBuilder
from chatbot.pokedex import Entities, Pokedex, normalize


@pytest.fixture(scope="module")
def dex():
    return Pokedex()


@pytest.fixture(scope="module")
def answers(dex):
    return AnswerBuilder(dex)


def ask(dex, answers, intent, question):
    return answers.answer(intent, question, dex.extract(question))


# ---- Entity extraction ------------------------------------------------------

def test_normalize_handles_accents_possessives_and_punctuation():
    assert normalize("Flabébé") == "flabebe"
    assert normalize("Bulbasaur's type?") == "bulbasaur type"
    assert normalize("Mr. Mime & Farfetch'd") == "mr mime farfetchd"


def test_extract_finds_each_kind(dex):
    e = dex.extract("Can Pikachu learn Thunderbolt with a Thunder Stone in Kanto? It's Electric")
    assert e.pokemon == ["pikachu"]
    assert e.moves == ["thunderbolt"]
    assert e.items == ["thunder-stone"]
    assert e.generations == [1]
    assert e.types == ["electric"]


def test_extract_prefers_longest_phrase(dex):
    e = dex.extract("What is Fire Blast?")
    assert e.moves == ["fire-blast"]
    assert e.types == []


def test_extract_squashed_names_plurals_and_generations(dex):
    assert dex.extract("What does a Pokéball do?").items == ["poke-ball"]
    assert dex.extract("where can I buy potions").items == ["potion"]
    assert dex.extract("legendaries in gen 4").generations == [4]


def test_extract_tolerates_typos_but_not_question_words(dex):
    assert dex.extract("tell me about pikachoo").pokemon == ["pikachu"]
    assert dex.extract("which starter is strongest").pokemon == []


def test_entities_merge_only_fills_empty_slots():
    merged = Entities(moves=["surf"]).merged_with(Entities(pokemon=["pikachu"], moves=["tackle"]))
    assert merged.pokemon == ["pikachu"]
    assert merged.moves == ["surf"]


# ---- Data helpers --------------------------------------------------------------

def test_type_effectiveness_stacks_for_dual_types(dex):
    assert dex.effectiveness("rock", ["fire", "flying"]) == 4.0
    assert dex.effectiveness("ground", ["flying"]) == 0.0


def test_evolution_lines_include_branches(dex):
    lines = dex.evolution_lines("eevee")
    assert len(lines) == 8
    assert "Eevee -> Jolteon (using a Thunder Stone)" in lines


# ---- Answers ----------------------------------------------------------------------

def test_pokemon_type(dex, answers):
    assert ask(dex, answers, "pokemon_type", "What type is Charizard?") == "Charizard is a Fire/Flying-type Pokémon."


def test_type_weakness_for_type_and_pokemon(dex, answers):
    fire = ask(dex, answers, "type_weakness", "What is Fire weak against?")
    assert fire.startswith("Fire type is weak to: Ground, Rock and Water (2x).")
    assert "super effective against: Bug, Steel, Grass and Ice" in fire
    assert "Rock (4x)" in ask(dex, answers, "type_weakness", "What is Charizard weak to?")


def test_type_immunity_attacker_and_defender_questions(dex, answers):
    assert ask(dex, answers, "type_immunity", "What is immune to Psychic?") == "Dark is immune to Psychic-type moves."
    assert ask(dex, answers, "type_immunity", "What is Ghost immune to?") == \
        "Ghost type is immune to Normal and Fighting-type moves."


def test_evolution_and_pre_evolution(dex, answers):
    assert "Charmeleon (at level 16) -> Charizard (at level 36)" in ask(
        dex, answers, "evolution", "What does Charmander evolve into?")
    assert ask(dex, answers, "pre_evolution", "What evolves into Pikachu?") == \
        "Pikachu evolves from Pichu on level up with high friendship."


def test_evolution_item_lookup_by_item(dex, answers):
    text = ask(dex, answers, "evolution_item", "What evolves with Thunder Stone?")
    assert "Pikachu -> Raichu" in text
    assert "Eevee -> Jolteon" in text


def test_move_info_and_learnsets(dex, answers):
    assert ask(dex, answers, "move_info", "Tell me about Thunderbolt").startswith(
        "Thunderbolt: Electric-type special move. Power 90, Accuracy 100%, PP 15.")
    assert ask(dex, answers, "move_learn", "Can Pikachu learn Surf?") == \
        "Pikachu learns Surf by TM in Scarlet / Violet."


def test_legendary_verdicts(dex, answers):
    assert ask(dex, answers, "legendary", "Is Dragonite legendary?").startswith(
        "No, Dragonite is not a Legendary or Mythical Pokémon.")
    assert ask(dex, answers, "legendary", "What legendaries are in Gen 1?") == \
        "Generation 1 (Kanto): Articuno, Zapdos, Moltres, Mewtwo and Mew (Mythical)"


def test_starters_filtered_by_region_and_type(dex, answers):
    assert ask(dex, answers, "starter", "What are the Kanto starters?") == \
        "Kanto (Gen 1): Bulbasaur (Grass/Poison), Charmander (Fire) and Squirtle (Water)"
    assert "Rowlet (Grass/Flying)" in ask(dex, answers, "starter", "What is the grass starter?")


def test_compare_two_pokemon(dex, answers):
    text = ask(dex, answers, "compare", "Charizard vs Blastoise")
    assert "Total: 534 vs 530" in text
    assert "Blastoise's own-type moves hit Charizard for up to 2x." in text


def test_open_ended_and_unsupported_questions_return_none(dex, answers):
    assert ask(dex, answers, "starter", "Which starter is best?") is None
    assert ask(dex, answers, "region", "Tell me about the Kanto gym leaders") is None
    assert ask(dex, answers, "team_build", "How do I build a team?") is None
    assert ask(dex, answers, "pokemon_type", "What type is it?") is None


def test_facts_cover_mentioned_entities(dex, answers):
    facts = answers.facts(dex.extract("Is Pikachu good with Surf?"))
    assert "Mouse Pokémon" in facts
    assert "Surf: Water-type special move" in facts


def test_fuzzy_match_requires_same_leading_letters(dex):
    assert dex.extract("hello there").pokemon == []
    assert dex.extract("what type is garchmop").pokemon == ["garchomp"]


def test_best_guess_describes_most_specific_entity(dex, answers):
    assert answers.best_guess(dex.extract("rare candy??")).startswith("Rare Candy (vitamins)")
    assert answers.best_guess(dex.extract("thunderbolt")).startswith("Thunderbolt: Electric-type")
    assert answers.best_guess(dex.extract("hmm")) is None


def test_evolution_between_two_pokemon_describes_the_path(dex, answers):
    assert ask(dex, answers, "evolution", "How do I evolve Eevee into Umbreon?") == \
        "Eevee evolves into Umbreon on level up with high friendship during the night."
    assert ask(dex, answers, "evolution", "Charmander to Charizard?") == (
        "Charmander evolves into Charmeleon at level 16.\nCharmeleon evolves into Charizard at level 36.")


def test_fuzzy_match_skips_english_words_but_fixes_typos_next_to_names(dex):
    assert dex.extract("What region is Sword and Shield?").pokemon == []
    assert dex.extract("Build me a team around Charizard").pokemon == ["charizard"]
    assert dex.extract("pikachoo vs raichu").pokemon == ["pikachu", "raichu"]


def test_open_ended_questions_wait_for_llm_unless_allowed(dex, answers):
    question = "Which starter is best in Sinnoh?"
    entities = dex.extract(question)
    assert answers.answer("starter", question, entities) is None
    assert "Turtwig (Grass)" in answers.answer("starter", question, entities, allow_open_ended=True)
