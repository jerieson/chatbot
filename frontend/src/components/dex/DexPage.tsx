import { useEffect, useState } from "react";
import { dexApi } from "@/services/dex";
import { dexHref } from "@/lib/dex";
import type { DexKind, Item, Move, Pokemon } from "@/types/dex";
import { SearchBar } from "@/components/dex/SearchBar";
import { PokemonView } from "@/components/dex/PokemonView";
import { MoveView } from "@/components/dex/MoveView";
import { ItemView } from "@/components/dex/ItemView";
import { PokemonSprite } from "@/components/dex/parts";

type Route = { kind: DexKind; slug: string; form?: string } | null;
type Entry = { kind: "pokemon"; data: Pokemon } | { kind: "move"; data: Move } | { kind: "item"; data: Item };

const FEATURED = [
  { id: 94, slug: "gengar", name: "Gengar" },
  { id: 25, slug: "pikachu", name: "Pikachu" },
  { id: 6, slug: "charizard", name: "Charizard" },
  { id: 133, slug: "eevee", name: "Eevee" },
  { id: 150, slug: "mewtwo", name: "Mewtwo" },
  { id: 448, slug: "lucario", name: "Lucario" },
  { id: 445, slug: "garchomp", name: "Garchomp" },
  { id: 248, slug: "tyranitar", name: "Tyranitar" },
];

const parseHash = (): Route => {
  // #/pokemon/gengar, or #/pokemon/gengar/gengar-mega to open a Mega form
  const match = window.location.hash.match(/^#\/(pokemon|move|item)\/([a-z0-9-]+)(?:\/([a-z0-9-]+))?$/);
  return match ? { kind: match[1] as DexKind, slug: match[2], form: match[3] } : null;
};

const useHashRoute = () => {
  const [route, setRoute] = useState<Route>(parseHash);
  useEffect(() => {
    const onChange = () => {
      setRoute(parseHash());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
};

export const DexPage = () => {
  const route = useHashRoute();
  const key = route ? `${route.kind}/${route.slug}` : null;
  // Results are stored with the route they belong to, so the status can be derived
  const [loaded, setLoaded] = useState<{ key: string; entry: Entry } | null>(null);
  const [failedKey, setFailedKey] = useState<string | null>(null);
  // Shiny stays on while browsing, so you can flip through shinies page by page
  const [shiny, setShiny] = useState(false);

  useEffect(() => {
    if (!key) {
      document.title = "EY-AY Pokédex";
      return;
    }
    let cancelled = false;
    const [kind, slug] = key.split("/");
    const load: Promise<Entry> =
      kind === "pokemon"
        ? dexApi.pokemon(slug).then((data) => ({ kind: "pokemon", data }))
        : kind === "move"
          ? dexApi.move(slug).then((data) => ({ kind: "move", data }))
          : dexApi.item(slug).then((data) => ({ kind: "item", data }));
    load
      .then((entry) => {
        if (cancelled) return;
        setLoaded({ key, entry });
        document.title = `${entry.data.name} · EY-AY Pokédex`;
      })
      .catch(() => !cancelled && setFailedKey(key));
    return () => {
      cancelled = true;
    };
  }, [key]);

  const entry = loaded?.entry ?? null; // keeps the previous page visible while the next one loads
  const status = !key ? "idle" : failedKey === key ? "error" : loaded?.key === key ? "idle" : "loading";

  return (
    <div className="flex min-h-screen flex-col bg-white text-zinc-900">
      <header className="border-b border-zinc-200 bg-zinc-50">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 py-5 sm:flex-row sm:gap-8">
          <a href="#/" className="font-pixel shrink-0 text-sm tracking-tight text-zinc-900">
            EY-AY <span className="text-red-600">DEX</span>
          </a>
          <SearchBar />
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        {!route ? (
          <Home />
        ) : status === "error" ? (
          <p className="py-20 text-center text-zinc-500">
            Couldn't load that entry. Is the backend running on port 8000?
          </p>
        ) : status === "loading" && !entry ? (
          <p className="py-20 text-center text-zinc-400">Loading…</p>
        ) : entry ? (
          <div className={status === "loading" ? "opacity-50 transition-opacity" : ""}>
            {entry.kind === "pokemon" && (
              <PokemonView
                key={`${entry.data.slug}/${route?.form ?? ""}`}
                pokemon={entry.data}
                initialForm={route?.form}
                shiny={shiny}
                onToggleShiny={() => setShiny((s) => !s)}
              />
            )}
            {entry.kind === "move" && <MoveView move={entry.data} />}
            {entry.kind === "item" && <ItemView item={entry.data} />}
          </div>
        ) : null}
      </main>

      <footer className="border-t border-zinc-200 py-6 text-center text-xs text-zinc-400">
        Data and sprites from <a href="https://pokeapi.co" className="underline">PokéAPI</a>. Pokémon is © Nintendo,
        Game Freak and Creatures.
      </footer>
    </div>
  );
};

const Home = () => (
  <div className="py-10 text-center">
    <h1 className="font-pixel mb-4 text-lg leading-relaxed sm:text-2xl">Pokédex</h1>
    <p className="mx-auto mb-10 max-w-md text-sm text-zinc-500">
      Look up any of the 1,025 Pokémon, 919 moves or 2,000+ items. Stats, type defenses, evolutions and full
      learnsets, with the classic pixel sprites.
    </p>
    <div className="mx-auto grid max-w-3xl grid-cols-4 gap-3 sm:grid-cols-8">
      {FEATURED.map((p) => (
        <a
          key={p.slug}
          href={dexHref("pokemon", p.slug)}
          className="flex flex-col items-center rounded-md p-2 transition hover:bg-zinc-100"
        >
          <PokemonSprite id={p.id} name={p.name} className="h-16 w-16" />
          <span className="mt-1 text-xs font-semibold text-sky-700">{p.name}</span>
        </a>
      ))}
    </div>
  </div>
);
