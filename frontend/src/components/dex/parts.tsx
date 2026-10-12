import { useState, type ReactNode } from "react";
import { TYPE_COLORS, dexHref, pokemonSprites, pokemonStaticSprite } from "@/lib/dex";

export const TypeBadge = ({ type, small = false }: { type: string; small?: boolean }) => (
  <span
    className={`inline-block rounded-[3px] text-center font-semibold uppercase tracking-wide text-white [text-shadow:0_1px_1px_rgb(0_0_0/0.35)] ${
      small ? "w-14 py-px text-[10px]" : "w-[4.5rem] py-0.5 text-[11px]"
    }`}
    style={{ backgroundColor: TYPE_COLORS[type] ?? "#999" }}
  >
    {type}
  </span>
);

/** Pixel-art sprite scaled up crisply. Tries each real sprite in turn (animated GIF, static PNG).
 *  If none exists but the Pokemon/form is confirmed in the data, shows a dark silhouette of the
 *  closest sprite we do have: the normal colors for a missing shiny, the base Pokemon for a form. */
export const PokemonSprite = ({
  id,
  name,
  className = "h-24 w-24",
  animated = true,
  shiny = false,
  silhouetteId,
}: {
  id: number;
  name: string;
  className?: string;
  animated?: boolean;
  shiny?: boolean;
  silhouetteId?: number; // base Pokemon whose sprite stands in for a form without one
}) => {
  const real = pokemonSprites(id, { animated, shiny });
  const silhouettes = [...(shiny ? [pokemonStaticSprite(id)] : []), ...(silhouetteId ? [pokemonStaticSprite(silhouetteId)] : [])];
  const sources = [...real, ...silhouettes];
  const key = `${id}-${animated}-${shiny}`;

  // Index into `sources`; stored with the sprite it belongs to so a new sprite starts over
  const [failed, setFailed] = useState({ key, step: 0 });
  const step = failed.key === key ? failed.step : 0;

  if (step >= sources.length) {
    return <div className={`${className} flex items-center justify-center text-2xl text-zinc-300`}>?</div>;
  }
  const isSilhouette = step >= real.length;
  return (
    <img
      src={sources[step]}
      alt={isSilhouette ? `${name} (sprite not available yet)` : name}
      title={isSilhouette ? "Sprite not available yet" : undefined}
      loading="lazy"
      className={`${className} object-contain [image-rendering:pixelated] ${
        isSilhouette ? "opacity-80 [filter:brightness(0)]" : ""
      }`}
      onError={() => setFailed({ key, step: step + 1 })}
    />
  );
};

export const ItemSprite = ({
  src,
  name,
  className = "h-16 w-16",
  hideIfMissing = false,
}: {
  src: string;
  name: string;
  className?: string;
  hideIfMissing?: boolean; // small inline icons just disappear instead of showing "?"
}) => {
  const [failed, setFailed] = useState(false);
  if (failed && hideIfMissing) return null;
  if (failed) return <div className={`${className} flex items-center justify-center text-2xl text-zinc-300`}>?</div>;
  return (
    <img
      src={src}
      alt={name}
      className={`${className} object-contain [image-rendering:pixelated]`}
      onError={() => setFailed(true)}
    />
  );
};

export const SectionTitle = ({ children }: { children: ReactNode }) => (
  <h2 className="mb-3 border-b border-zinc-200 pb-1.5 text-lg font-bold text-zinc-800">{children}</h2>
);

/** One row of a pokemondb-style data table: muted label on the left, value on the right. */
export const DataRow = ({ label, children }: { label: string; children: ReactNode }) => (
  <tr className="border-b border-zinc-100 last:border-0">
    <th className="w-[38%] py-1.5 pr-3 text-right align-top text-xs font-normal text-zinc-500">{label}</th>
    <td className="py-1.5 text-sm text-zinc-800">{children}</td>
  </tr>
);

export const DataTable = ({ title, children }: { title: string; children: ReactNode }) => (
  <div>
    <SectionTitle>{title}</SectionTitle>
    <table className="w-full">
      <tbody>{children}</tbody>
    </table>
  </div>
);

export const DexLink = ({ kind, slug, children }: { kind: string; slug: string; children: ReactNode }) => (
  <a href={dexHref(kind, slug)} className="font-semibold text-sky-700 hover:text-sky-900 hover:underline">
    {children}
  </a>
);
