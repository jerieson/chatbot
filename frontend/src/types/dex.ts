export type DexKind = "pokemon" | "move" | "item";

export type Stats = Record<"hp" | "attack" | "defense" | "sp_attack" | "sp_defense" | "speed", number>;

export interface PokemonSummary {
  slug: string;
  name: string;
  id: number;
  types: string[];
}

export type SearchResult =
  | ({ kind: "pokemon"; form?: string } & PokemonSummary)
  | { kind: "move"; slug: string; name: string; type: string }
  | { kind: "item"; slug: string; name: string; category: string };

export interface MoveRow {
  slug: string;
  name: string;
  type: string;
  damage_class: string;
  power: number | null;
  accuracy: number | null;
  level?: number;
}

export interface EvolutionNode extends PokemonSummary {
  method: string | null;
  evolves_to: EvolutionNode[];
}

export interface Ability {
  slug: string;
  name?: string;
  effect?: string;
  hidden: boolean;
}

export interface MoveLists {
  game: string | null;
  level_up: MoveRow[];
  machine: MoveRow[];
  egg: MoveRow[];
}

/** Regional form, Mega Evolution or Primal Reversion, with its own types, stats and abilities. */
export interface PokemonForm {
  slug: string;
  id: number;
  name: string;
  kind: "regional" | "mega" | "primal";
  region: string | null; // Alola, Galar, Hisui, Paldea (regional forms)
  moves: MoveLists | null; // regional forms have their own learnset; null = same as the base form
  item: { slug: string; name: string } | null; // Mega Stone or orb
  move: { slug: string; name: string } | null; // Mega Rayquaza: Dragon Ascent
  types: string[];
  stats: Stats;
  stat_total: number;
  abilities: Ability[];
  ev_yield: Partial<Stats>;
  height_m: number;
  weight_kg: number;
  type_defenses: Record<string, number>;
}

export interface Pokemon extends PokemonSummary {
  genus: string;
  generation: number;
  stats: Stats;
  stat_total: number;
  height_m: number;
  weight_kg: number;
  legendary: boolean;
  mythical: boolean;
  flavor_text: string;
  abilities: Ability[];
  forms: PokemonForm[];
  ev_yield: Partial<Stats>;
  catch_rate: number | null;
  base_friendship: number | null;
  base_experience: number | null;
  growth_rate: string;
  egg_groups: string[];
  gender_rate: number | null; // eighths female, -1 = genderless
  egg_cycles: number | null;
  type_defenses: Record<string, number>;
  evolution: EvolutionNode;
  moves: MoveLists;
  previous: PokemonSummary | null;
  next: PokemonSummary | null;
}

export interface Move {
  slug: string;
  name: string;
  type: string;
  damage_class: string;
  power: number | null;
  accuracy: number | null;
  pp: number | null;
  priority: number;
  generation: number;
  effect: string;
  learned_by: (PokemonSummary & { how: string })[];
}

export interface Item {
  slug: string;
  name: string;
  category: string;
  cost: number | null;
  effect: string;
  mega_forms: (PokemonSummary & { species: string; species_name: string; species_id: number })[];
}
