import { dexHref, itemSprite, titleCase } from "@/lib/dex";
import type { Item } from "@/types/dex";
import { DataRow, DataTable, ItemSprite, PokemonSprite, SectionTitle, TypeBadge } from "@/components/dex/parts";

export const ItemView = ({ item: i }: { item: Item }) => (
  <article>
    <h1 className="mb-1 text-center text-3xl font-bold text-zinc-900">{i.name}</h1>
    <p className="mb-8 text-center text-sm text-zinc-500">Item · {titleCase(i.category)}</p>

    <div className="grid gap-8 md:grid-cols-[1fr_1.2fr_1.4fr]">
      <div className="flex h-40 items-center justify-center rounded-md border border-zinc-200 bg-zinc-50">
        <ItemSprite key={i.slug} src={itemSprite(i.slug)} name={i.name} className="h-24 w-24" />
      </div>

      <DataTable title="Item data">
        <DataRow label="Category">{titleCase(i.category)}</DataRow>
        <DataRow label="Buy price">{i.cost ? `₽${i.cost.toLocaleString()}` : "Can't be bought"}</DataRow>
        {i.cost ? <DataRow label="Sell price">₽{Math.floor(i.cost / 2).toLocaleString()}</DataRow> : null}
      </DataTable>

      <div>
        <SectionTitle>Effect</SectionTitle>
        <p className="text-sm leading-relaxed text-zinc-700">{i.effect || "No description available."}</p>
      </div>
    </div>

    {i.mega_forms.length > 0 && (
      <section className="mt-10">
        <SectionTitle>{i.mega_forms.some((f) => f.slug.endsWith("-primal")) ? "Primal Reversion" : "Mega Evolution"}</SectionTitle>
        <div className="flex flex-wrap gap-4">
          {i.mega_forms.map((f) => (
            <a
              key={f.slug}
              href={dexHref("pokemon", f.species, f.slug)}
              className="flex items-center gap-4 rounded-md border border-zinc-200 p-3 pr-6 transition hover:border-zinc-400 hover:bg-zinc-50"
            >
              <PokemonSprite id={f.id} name={f.name} className="h-20 w-20" silhouetteId={f.species_id} />
              <span>
                <span className="block text-xs text-zinc-500">{i.name} lets {f.species_name} become</span>
                <span className="mb-1 block font-semibold text-sky-700">{f.name}</span>
                <span className="flex gap-1">
                  {f.types.map((t) => (
                    <TypeBadge key={t} type={t} small />
                  ))}
                </span>
              </span>
            </a>
          ))}
        </div>
      </section>
    )}
  </article>
);
