import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Search } from "lucide-react";
import { dexApi } from "@/services/dex";
import { dexHref, dexNumber, itemSprite, titleCase } from "@/lib/dex";
import type { SearchResult } from "@/types/dex";
import { ItemSprite, PokemonSprite, TypeBadge } from "@/components/dex/parts";

/** Search box with suggestions as you type; Enter opens the highlighted (or first) result. */
export const SearchBar = () => {
  const [query, setQuery] = useState("");
  // Results remember their query, so stale ones are never shown for new text
  const [found, setFound] = useState<{ q: string; results: SearchResult[] }>({ q: "", results: [] });
  const [highlight, setHighlight] = useState(0);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = query.trim();
    if (!q) return;
    // Wait for a pause in typing, and drop responses for queries that are out of date
    const controller = new AbortController();
    const timer = setTimeout(() => {
      dexApi
        .search(q, controller.signal)
        .then((results) => {
          setFound({ q, results });
          setHighlight(0);
        })
        .catch(() => {});
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const go = (r: SearchResult) => {
    window.location.hash = dexHref(r.kind, r.slug, r.kind === "pokemon" ? r.form : undefined);
    setQuery("");
    setOpen(false);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter" && results[highlight]) {
      go(results[highlight]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const results = found.q === query.trim() ? found.results : [];
  const searching = found.q !== query.trim();
  const showList = open && query.trim() !== "";

  return (
    <div ref={boxRef} className="relative mx-auto w-full max-w-xl">
      <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Search a Pokémon, move or item…  (e.g. Gengar, Shadow Ball, #94)"
        aria-label="Search the Pokédex"
        className="w-full rounded-md border border-zinc-300 bg-white py-2.5 pl-10 pr-4 text-sm shadow-sm outline-none transition focus:border-sky-600 focus:ring-2 focus:ring-sky-600/20"
      />

      {showList && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-zinc-200 bg-white shadow-lg">
          {results.length === 0 ? (
            <li className="px-4 py-3 text-sm text-zinc-500">{searching ? "Searching…" : "No matches."}</li>
          ) : (
            results.map((r, i) => (
              <li key={`${r.kind}-${r.slug}-${r.kind === "pokemon" ? (r.form ?? "") : ""}`}>
                <button
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => go(r)}
                  onMouseEnter={() => setHighlight(i)}
                  className={`flex w-full items-center gap-3 px-3 py-1.5 text-left text-sm ${
                    i === highlight ? "bg-sky-50" : ""
                  }`}
                >
                  {r.kind === "pokemon" ? (
                    <PokemonSprite id={r.id} name={r.name} className="h-10 w-10" animated={false} />
                  ) : r.kind === "item" ? (
                    <ItemSprite key={r.slug} src={itemSprite(r.slug)} name={r.name} className="h-8 w-10" />
                  ) : (
                    <span className="flex h-10 w-10 items-center justify-center text-[10px] font-semibold uppercase text-zinc-400">
                      Move
                    </span>
                  )}
                  <span className="flex-1 font-semibold text-zinc-800">
                    {r.name}
                    {r.kind === "pokemon" && <span className="ml-2 text-xs font-normal text-zinc-400">#{dexNumber(r.id)}</span>}
                  </span>
                  <span className="flex gap-1">
                    {r.kind === "pokemon" && r.types.map((t) => <TypeBadge key={t} type={t} small />)}
                    {r.kind === "move" && <TypeBadge type={r.type} small />}
                    {r.kind === "item" && <span className="text-xs text-zinc-500">{titleCase(r.category)}</span>}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
};
