import { dexHref, dexNumber } from "@/lib/dex";
import type { Move } from "@/types/dex";
import { DataRow, DataTable, PokemonSprite, SectionTitle, TypeBadge } from "@/components/dex/parts";
import { CategoryIcon } from "@/components/dex/PokemonView";

export const MoveView = ({ move: m }: { move: Move }) => (
  <article>
    <h1 className="mb-1 text-center text-3xl font-bold text-zinc-900">{m.name}</h1>
    <p className="mb-8 text-center text-sm text-zinc-500">Move · introduced in Generation {m.generation}</p>

    <div className="grid gap-8 md:grid-cols-2">
      <DataTable title="Move data">
        <DataRow label="Type">
          <TypeBadge type={m.type} />
        </DataRow>
        <DataRow label="Category">
          <CategoryIcon category={m.damage_class} />
        </DataRow>
        <DataRow label="Power">{m.power ?? "—"}</DataRow>
        <DataRow label="Accuracy">{m.accuracy ?? "—"}</DataRow>
        <DataRow label="PP">{m.pp ?? "—"}</DataRow>
        <DataRow label="Priority">{m.priority > 0 ? `+${m.priority}` : m.priority}</DataRow>
      </DataTable>

      <div>
        <SectionTitle>Effect</SectionTitle>
        <p className="text-sm leading-relaxed text-zinc-700">{m.effect || "No description available."}</p>
      </div>
    </div>

    <section className="mt-10">
      <SectionTitle>
        Learned by {m.learned_by.length} Pokémon
      </SectionTitle>
      {m.learned_by.length === 0 ? (
        <p className="text-sm text-zinc-500">No Pokémon learns this move in the latest games.</p>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(10.5rem,1fr))] gap-2">
          {m.learned_by.map((p) => (
            <a
              key={p.slug}
              href={dexHref("pokemon", p.slug)}
              className="flex items-center gap-2 rounded-md border border-zinc-100 p-1.5 transition hover:border-zinc-300 hover:bg-zinc-50"
            >
              <PokemonSprite id={p.id} name={p.name} className="h-12 w-12" animated={false} />
              <span className="min-w-0">
                <span className="block text-[10px] text-zinc-400">#{dexNumber(p.id)}</span>
                <span className="block truncate text-sm font-semibold text-sky-700">{p.name}</span>
                <span className="block text-[10px] text-zinc-500">{p.how}</span>
              </span>
            </a>
          ))}
        </div>
      )}
    </section>
  </article>
);

