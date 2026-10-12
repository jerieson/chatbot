import { useState } from "react";
import { ChevronLeft, ChevronRight, Star } from "lucide-react";
import {
  STAT_LABELS,
  TYPE_COLORS,
  TYPE_ORDER,
  dexHref,
  dexNumber,
  formatGender,
  formatHeight,
  formatMultiplier,
  formatWeight,
  itemSprite,
  statColor,
  statRange,
  titleCase,
} from "@/lib/dex";
import type { EvolutionNode, MegaForm, MoveRow, Pokemon, Stats } from "@/types/dex";
import { DataRow, DataTable, DexLink, ItemSprite, PokemonSprite, SectionTitle, TypeBadge } from "@/components/dex/parts";

interface PokemonViewProps {
  pokemon: Pokemon;
  initialForm?: string; // Mega form slug from the URL, e.g. #/pokemon/gengar/gengar-mega
  shiny: boolean;
  onToggleShiny: () => void;
}

export const PokemonView = ({ pokemon: p, initialForm, shiny, onToggleShiny }: PokemonViewProps) => {
  const [formSlug, setFormSlug] = useState(initialForm ?? null);
  const form: MegaForm | undefined = p.megas.find((m) => m.slug === formSlug);
  // Everything that changes with Mega Evolution comes from the selected form
  const shown = form ?? p;
  const displayName = form?.name ?? p.name;

  const evYield = Object.entries(shown.ev_yield)
    .map(([stat, n]) => `${n} ${STAT_LABELS[stat]}`)
    .join(", ");

  return (
    <article>
      <PrevNext pokemon={p} />

      <h1 className="mb-1 text-center text-3xl font-bold text-zinc-900">{displayName}</h1>
      <p className="mb-6 text-center text-sm text-zinc-500">
        {p.legendary ? "Legendary " : p.mythical ? "Mythical " : ""}
        {p.genus} · Generation {p.generation}
      </p>

      <div className="grid gap-8 md:grid-cols-[1fr_1.15fr_1fr]">
        <div className="flex flex-col items-center gap-3">
          <div className="relative flex h-56 w-full items-center justify-center rounded-md border border-zinc-200 bg-zinc-50">
            <PokemonSprite
              id={form?.id ?? p.id}
              name={displayName}
              shiny={shiny}
              silhouetteId={form ? p.id : undefined}
              className="h-40 w-40"
            />
            <button
              onClick={onToggleShiny}
              aria-pressed={shiny}
              aria-label={shiny ? "Show normal colors" : "Show shiny colors"}
              title={shiny ? "Shiny (click for normal colors)" : "Show shiny"}
              className={`absolute right-2 top-2 rounded-full border p-1.5 transition ${
                shiny
                  ? "border-amber-300 bg-amber-50 text-amber-500"
                  : "border-zinc-200 bg-white text-zinc-400 hover:text-amber-500"
              }`}
            >
              <Star className="h-4 w-4" fill={shiny ? "currentColor" : "none"} />
            </button>
          </div>

          {p.megas.length > 0 && <FormTabs pokemon={p} selected={formSlug} onSelect={setFormSlug} />}
          {form && <FormTrigger form={form} baseName={p.name} />}

          {p.flavor_text && <p className="text-center text-sm italic text-zinc-600">“{p.flavor_text}”</p>}
        </div>

        <DataTable title="Pokédex data">
          <DataRow label="National №">
            <strong>{dexNumber(p.id)}</strong>
          </DataRow>
          <DataRow label="Type">
            <span className="flex gap-1">
              {shown.types.map((t) => (
                <TypeBadge key={t} type={t} />
              ))}
            </span>
          </DataRow>
          <DataRow label="Species">{p.genus}</DataRow>
          <DataRow label="Height">{formatHeight(shown.height_m)}</DataRow>
          <DataRow label="Weight">{formatWeight(shown.weight_kg)}</DataRow>
          <DataRow label="Abilities">
            {shown.abilities.length === 0 && <span className="text-zinc-400">Not in the data yet</span>}
            <ol className="space-y-0.5">
              {shown.abilities.map((a, i) => (
                <li key={a.slug} title={a.effect}>
                  {a.hidden ? (
                    <span className="text-xs text-zinc-600">
                      {a.name ?? titleCase(a.slug)} <span className="text-zinc-400">(hidden ability)</span>
                    </span>
                  ) : (
                    <span>
                      {i + 1}. {a.name ?? titleCase(a.slug)}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </DataRow>
        </DataTable>

        <div className="space-y-6">
          <DataTable title="Training">
            <DataRow label="EV yield">{evYield || "—"}</DataRow>
            <DataRow label="Catch rate">{p.catch_rate ?? "—"}</DataRow>
            <DataRow label="Base Friendship">{p.base_friendship ?? "—"}</DataRow>
            <DataRow label="Base Exp.">{p.base_experience ?? "—"}</DataRow>
            <DataRow label="Growth Rate">{p.growth_rate ? titleCase(p.growth_rate) : "—"}</DataRow>
          </DataTable>
          <DataTable title="Breeding">
            <DataRow label="Egg Groups">{p.egg_groups.join(", ") || "—"}</DataRow>
            <DataRow label="Gender">{formatGender(p.gender_rate)}</DataRow>
            <DataRow label="Egg cycles">{p.egg_cycles ?? "—"}</DataRow>
          </DataTable>
        </div>
      </div>

      <div className="mt-10 grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        <BaseStats stats={shown.stats} total={shown.stat_total} />
        <TypeDefenses defenses={shown.type_defenses} name={displayName} />
      </div>

      <section className="mt-10">
        <SectionTitle>Evolution chart</SectionTitle>
        {p.evolution.evolves_to.length ? (
          <div className="overflow-x-auto pb-2">
            <EvolutionBranch node={p.evolution} current={p.slug} />
          </div>
        ) : (
          <p className="text-sm text-zinc-500">{p.name} does not evolve.</p>
        )}
      </section>

      <section className="mt-10">
        <SectionTitle>Moves learned by {p.name}</SectionTitle>
        {p.moves.game && <p className="-mt-1 mb-4 text-xs text-zinc-500">From Pokémon {p.moves.game}</p>}
        <div className="grid gap-8 lg:grid-cols-2">
          <MoveTable title="By level up" moves={p.moves.level_up} showLevel />
          <div className="space-y-8">
            <MoveTable title="By TM" moves={p.moves.machine} />
            {p.moves.egg.length > 0 && <MoveTable title="Egg moves" moves={p.moves.egg} />}
          </div>
        </div>
      </section>
    </article>
  );
};

/** Base form plus one tab per Mega/Primal form; Mega tabs show their stone. */
const FormTabs = ({
  pokemon: p,
  selected,
  onSelect,
}: {
  pokemon: Pokemon;
  selected: string | null;
  onSelect: (slug: string | null) => void;
}) => {
  const tab = (active: boolean) =>
    `flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-semibold transition ${
      active ? "border-zinc-800 bg-zinc-800 text-white" : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400"
    }`;
  return (
    <div className="flex flex-wrap justify-center gap-1.5" role="tablist" aria-label="Forms">
      <button role="tab" aria-selected={!selected} onClick={() => onSelect(null)} className={tab(!selected)}>
        {p.name}
      </button>
      {p.megas.map((m) => (
        <button
          key={m.slug}
          role="tab"
          aria-selected={selected === m.slug}
          onClick={() => onSelect(m.slug)}
          className={tab(selected === m.slug)}
          title={m.item ? `Holding ${m.item.name}` : m.move ? `Knowing ${m.move.name}` : undefined}
        >
          {m.item && <ItemSprite key={m.item.slug} src={itemSprite(m.item.slug)} name="" className="h-5 w-5" hideIfMissing />}
          {m.name}
        </button>
      ))}
    </div>
  );
};

/** How the selected form is reached: the stone/orb to hold, or the move to know (Rayquaza). */
const FormTrigger = ({ form, baseName }: { form: MegaForm; baseName: string }) => {
  const how = form.item
    ? { verb: "holding", kind: "item", ...form.item }
    : form.move
      ? { verb: "knowing", kind: "move", ...form.move }
      : null;
  return (
    <p className="text-center text-xs text-zinc-600">
      {form.kind === "primal" ? "Primal Reversion" : "Mega Evolves"} from {baseName}
      {how && (
        <>
          {` ${how.verb} `}
          <DexLink kind={how.kind} slug={how.slug}>
            {how.name}
          </DexLink>
        </>
      )}
    </p>
  );
};

const PrevNext = ({ pokemon: p }: { pokemon: Pokemon }) => (
  <nav className="mb-4 flex justify-between text-sm">
    {p.previous ? (
      <a
        href={dexHref("pokemon", p.previous.slug)}
        className="flex items-center gap-1 text-zinc-500 hover:text-sky-700"
      >
        <ChevronLeft className="h-4 w-4" />#{dexNumber(p.previous.id)} {p.previous.name}
      </a>
    ) : (
      <span />
    )}
    {p.next && (
      <a href={dexHref("pokemon", p.next.slug)} className="flex items-center gap-1 text-zinc-500 hover:text-sky-700">
        #{dexNumber(p.next.id)} {p.next.name}
        <ChevronRight className="h-4 w-4" />
      </a>
    )}
  </nav>
);

const BaseStats = ({ stats, total }: { stats: Stats; total: number }) => (
  <section>
    <SectionTitle>Base stats</SectionTitle>
    <table className="w-full text-sm">
      <thead>
        <tr className="text-[11px] text-zinc-400">
          <th />
          <th />
          <th />
          <th className="w-12 text-right font-normal">Min</th>
          <th className="w-12 text-right font-normal">Max</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(stats).map(([stat, value]) => {
          const [min, max] = statRange(stat, value);
          return (
            <tr key={stat} className="border-b border-zinc-100">
              <th className="w-20 py-1.5 pr-2 text-right text-xs font-normal text-zinc-500">{STAT_LABELS[stat]}</th>
              <td className="w-10 py-1.5 pr-2 text-right font-semibold">{value}</td>
              <td className="py-1.5">
                <div
                  className="h-3 rounded-sm"
                  style={{ width: `${Math.min(100, (value / 255) * 100)}%`, backgroundColor: statColor(value) }}
                />
              </td>
              <td className="py-1.5 text-right text-zinc-600">{min}</td>
              <td className="py-1.5 text-right text-zinc-600">{max}</td>
            </tr>
          );
        })}
        <tr>
          <th className="py-1.5 pr-2 text-right text-xs font-normal text-zinc-500">Total</th>
          <td className="py-1.5 pr-2 text-right font-bold">{total}</td>
          <td colSpan={3} className="py-1.5 text-[11px] text-zinc-400">
            Min/max at level 100: no IVs/EVs with a hindering nature, up to 31 IVs, 252 EVs, helpful nature.
          </td>
        </tr>
      </tbody>
    </table>
  </section>
);

const MULTIPLIER_STYLES: Record<string, string> = {
  "0": "bg-zinc-800 text-white",
  "¼": "bg-red-800 text-white",
  "½": "bg-red-600 text-white",
  "2": "bg-green-600 text-white",
  "4": "bg-green-800 text-white",
};

const TypeDefenses = ({ defenses, name }: { defenses: Record<string, number>; name: string }) => (
  <section>
    <SectionTitle>Type defenses</SectionTitle>
    <p className="-mt-1 mb-3 text-xs text-zinc-500">The effectiveness of each type on {name}.</p>
    <div className="grid grid-cols-9 gap-px overflow-hidden rounded-sm border border-zinc-200 bg-zinc-200">
      {TYPE_ORDER.map((type) => {
        const label = formatMultiplier(defenses[type] ?? 1);
        return (
          <div key={type} className="bg-white text-center" title={`${type}: ×${defenses[type] ?? 1}`}>
            <div
              className="py-0.5 text-[10px] font-semibold uppercase text-white [text-shadow:0_1px_1px_rgb(0_0_0/0.35)]"
              style={{ backgroundColor: TYPE_COLORS[type] }}
            >
              {type.slice(0, 3)}
            </div>
            <div className={`py-1 text-sm font-semibold ${MULTIPLIER_STYLES[label] ?? ""}`}>{label || " "}</div>
          </div>
        );
      })}
    </div>
  </section>
);

/** Evolution tree: a Pokemon, then an arrow with the method for each branch. */
const EvolutionBranch = ({ node, current }: { node: EvolutionNode; current: string }) => {
  // Many final branches (Eevee has eight): a compact grid instead of a tall column
  const wide = node.evolves_to.length > 3 && node.evolves_to.every((c) => c.evolves_to.length === 0);
  if (wide) {
    return (
      <div className="flex items-center gap-4">
        <EvolutionCard node={node} current={current} />
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          {node.evolves_to.map((child) => (
            <div key={child.slug} className="flex flex-col items-center">
              <EvolutionCard node={child} current={current} />
              {child.method && (
                <span className="w-32 text-center text-[11px] leading-tight text-zinc-500">({child.method})</span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <EvolutionCard node={node} current={current} />
      {node.evolves_to.length > 0 && (
        <div className="flex flex-col gap-3">
          {node.evolves_to.map((child) => (
            <div key={child.slug} className="flex items-center gap-2">
              <div className="flex w-28 shrink-0 flex-col items-center text-center text-[11px] leading-tight text-zinc-500">
                <span className="text-lg text-zinc-400">→</span>
                {child.method && <span>({child.method})</span>}
              </div>
              <EvolutionBranch node={child} current={current} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const EvolutionCard = ({ node, current }: { node: EvolutionNode; current: string }) => (
  <a
    href={dexHref("pokemon", node.slug)}
    className={`flex w-28 shrink-0 flex-col items-center rounded-md p-1.5 text-center transition hover:bg-zinc-100 ${
      node.slug === current ? "bg-zinc-100 ring-1 ring-zinc-300" : ""
    }`}
  >
    <PokemonSprite id={node.id} name={node.name} className="h-20 w-20" animated={false} />
    <span className="text-[11px] text-zinc-400">#{dexNumber(node.id)}</span>
    <span className="text-sm font-semibold text-sky-700">{node.name}</span>
    <span className="text-[10px] text-zinc-500">{node.types.map(titleCase).join(" · ")}</span>
  </a>
);

export const MoveTable = ({
  title,
  moves,
  showLevel = false,
}: {
  title: string;
  moves: MoveRow[];
  showLevel?: boolean;
}) => (
  <div>
    <h3 className="mb-2 text-sm font-bold text-zinc-700">{title}</h3>
    {moves.length === 0 ? (
      <p className="text-sm text-zinc-500">None.</p>
    ) : (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-zinc-200 text-left text-xs text-zinc-500">
              {showLevel && <th className="py-1.5 pr-2 font-semibold">Lv.</th>}
              <th className="py-1.5 pr-2 font-semibold">Move</th>
              <th className="py-1.5 pr-2 font-semibold">Type</th>
              <th className="py-1.5 pr-2 font-semibold">Cat.</th>
              <th className="py-1.5 pr-2 text-right font-semibold">Power</th>
              <th className="py-1.5 text-right font-semibold">Acc.</th>
            </tr>
          </thead>
          <tbody>
            {moves.map((m, i) => (
              <tr key={`${m.slug}-${i}`} className="border-b border-zinc-100 hover:bg-zinc-50">
                {showLevel && <td className="py-1 pr-2 text-zinc-600">{m.level || "—"}</td>}
                <td className="py-1 pr-2">
                  <DexLink kind="move" slug={m.slug}>
                    {m.name}
                  </DexLink>
                </td>
                <td className="py-1 pr-2">
                  <TypeBadge type={m.type} small />
                </td>
                <td className="py-1 pr-2">
                  <CategoryIcon category={m.damage_class} />
                </td>
                <td className="py-1 pr-2 text-right text-zinc-700">{m.power ?? "—"}</td>
                <td className="py-1 text-right text-zinc-700">{m.accuracy ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
);

const CATEGORY_STYLES: Record<string, string> = {
  physical: "bg-orange-600",
  special: "bg-indigo-600",
  status: "bg-zinc-400",
};

export const CategoryIcon = ({ category }: { category: string }) => (
  <span
    title={titleCase(category)}
    className={`inline-block rounded-sm px-1.5 py-px text-[10px] font-semibold uppercase text-white ${
      CATEGORY_STYLES[category] ?? "bg-zinc-400"
    }`}
  >
    {category.slice(0, 4)}
  </span>
);
