// Pokedex display helpers: sprites (PokeAPI's free sprite repo), type colors, formatting

const SPRITES = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites";
const LAST_ANIMATED = 649; // Black/White animated sprites stop at Genesect

/** Retro sprites to try in order: animated Black/White pixel art (#1-649), then the static pixel sprite.
 *  Mega forms use their own ids (10000+), which only have static sprites. */
export const pokemonSprites = (id: number, { animated = true, shiny = false } = {}) => {
  const shinyDir = shiny ? "shiny/" : "";
  const urls = [`${SPRITES}/pokemon/${shinyDir}${id}.png`];
  if (animated && id <= LAST_ANIMATED) {
    urls.unshift(`${SPRITES}/pokemon/versions/generation-v/black-white/animated/${shinyDir}${id}.gif`);
  }
  return urls;
};

export const pokemonStaticSprite = (id: number) => `${SPRITES}/pokemon/${id}.png`;

export const itemSprite = (slug: string) => `${SPRITES}/items/${slug}.png`;

export const TYPE_COLORS: Record<string, string> = {
  normal: "#A8A77A",
  fire: "#EE8130",
  water: "#6390F0",
  electric: "#F7D02C",
  grass: "#7AC74C",
  ice: "#96D9D6",
  fighting: "#C22E28",
  poison: "#A33EA1",
  ground: "#E2BF65",
  flying: "#A98FF3",
  psychic: "#F95587",
  bug: "#A6B91A",
  rock: "#B6A136",
  ghost: "#735797",
  dragon: "#6F35FC",
  dark: "#705746",
  steel: "#B7B7CE",
  fairy: "#D685AD",
};

export const TYPE_ORDER = Object.keys(TYPE_COLORS);

export const STAT_LABELS: Record<string, string> = {
  hp: "HP",
  attack: "Attack",
  defense: "Defense",
  sp_attack: "Sp. Atk",
  sp_defense: "Sp. Def",
  speed: "Speed",
};

/** pokemondb-style bar colors: red for low stats through green/teal for high ones. */
export const statColor = (value: number) =>
  value < 30 ? "#f34444" : value < 60 ? "#ff7f0f" : value < 90 ? "#ffdd57" : value < 120 ? "#a0e515" : value < 150 ? "#23cd5e" : "#00c2b8";

/** Level 100 stat range: 0 IV / 0 EV / hindering nature up to 31 IV / 252 EV / helpful nature. */
export const statRange = (stat: string, base: number): [number, number] =>
  stat === "hp"
    ? [2 * base + 110, 2 * base + 204]
    : [Math.floor((2 * base + 5) * 0.9), Math.floor((2 * base + 99) * 1.1)];

export const dexNumber = (id: number) => String(id).padStart(4, "0");

export const titleCase = (text: string) => text.replace(/\b\w/g, (c) => c.toUpperCase());

export const formatHeight = (m: number) => {
  const inches = Math.round(m * 39.3701);
  return `${m.toFixed(1)} m (${Math.floor(inches / 12)}′${String(inches % 12).padStart(2, "0")}″)`;
};

export const formatWeight = (kg: number) => `${kg.toFixed(1)} kg (${(kg * 2.20462).toFixed(1)} lbs)`;

export const formatGender = (rate: number | null) => {
  if (rate === null) return "—";
  if (rate < 0) return "Genderless";
  const female = (rate / 8) * 100;
  return `${100 - female}% male, ${female}% female`;
};

export const formatMultiplier = (m: number) =>
  m === 1 ? "" : m === 0 ? "0" : m === 0.25 ? "¼" : m === 0.5 ? "½" : String(m);

/** Hash routes like #/pokemon/gengar so links, back/forward and refresh all work. */
export const dexHref = (kind: string, slug: string, form?: string) => `#/${kind}/${slug}${form ? `/${form}` : ""}`;
