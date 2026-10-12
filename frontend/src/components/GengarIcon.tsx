// The bot's face: the Gengar grin (public/gengar-face.png) on a dark purple sphere,
// optionally wrapped in animated purple/black flames (styles in index.css).

interface FlameLayer {
  color: string;
  count: number;
  minLength: number;
  maxLength: number;
  width: number;
  spin: string; // CSS class that rotates the whole layer
  offset: number; // degrees, so layers interleave
}

// The face disc has radius 30 in a 100x100 box; tongues grow outward from its edge
const DISC_RADIUS = 30;
const LAYERS: FlameLayer[] = [
  { color: "var(--color-gengar-950)", count: 11, minLength: 13, maxLength: 20, width: 10, spin: "flame-spin", offset: 0 },
  { color: "var(--color-gengar-700)", count: 11, minLength: 9, maxLength: 15, width: 8, spin: "flame-spin-reverse", offset: 16 },
  { color: "var(--color-gengar-400)", count: 9, minLength: 5, maxLength: 9, width: 6, spin: "flame-spin", offset: 8 },
];

/** One flame tongue rising from the disc's top edge: a wide base that curls into a thin tip. */
function tonguePath(length: number, width: number, lean: number): string {
  const base = 50 - DISC_RADIUS + 4; // start inside the disc so there is no gap
  const tip = 50 - DISC_RADIUS - length;
  const f = (n: number) => n.toFixed(1);
  return (
    `M ${f(50 - width)} ${f(base)} ` +
    `C ${f(50 - width * 1.15)} ${f(base - length * 0.45)}, ${f(50 + lean * 0.2 - width * 0.35)} ${f(tip + length * 0.4)}, ${f(50 + lean)} ${f(tip)} ` +
    `C ${f(50 + lean * 0.35 + width * 0.45)} ${f(tip + length * 0.5)}, ${f(50 + width * 1.1)} ${f(base - length * 0.3)}, ${f(50 + width)} ${f(base)} Z`
  );
}

// Deterministic "random" so every render (and the favicon) draws the same flames
const jitter = (i: number, salt: number) => ((i * 37 + salt * 11) % 10) / 10;

const Flames = () => (
  <svg viewBox="0 0 100 100" aria-hidden="true" className="flames pointer-events-none absolute inset-[-33%] overflow-visible">
    {LAYERS.map((layer, li) => (
      <g key={li} className={layer.spin} fill={layer.color}>
        {Array.from({ length: layer.count }, (_, i) => {
          const angle = layer.offset + (360 / layer.count) * i;
          const length = layer.minLength + (layer.maxLength - layer.minLength) * jitter(i, li);
          const lean = (jitter(i, li + 3) - 0.5) * layer.width * 2.2;
          return (
            <g key={i} transform={`rotate(${angle} 50 50)`}>
              <path
                className="flame-tongue"
                d={tonguePath(length, layer.width, lean)}
                style={{
                  animationDelay: `${-jitter(i, li + 5) * 1.5}s`,
                  animationDuration: `${0.9 + jitter(i, li + 7) * 0.8}s`,
                }}
              />
            </g>
          );
        })}
      </g>
    ))}
  </svg>
);

interface GengarIconProps {
  className?: string; // size of the face disc, e.g. "h-7 w-7"; flames extend beyond it
  flames?: boolean;
}

export const GengarIcon = ({ className = "h-7 w-7", flames = false }: GengarIconProps) => (
  <span className={`relative inline-flex shrink-0 ${className}`}>
    {flames && <Flames />}
    <span className="relative inline-flex h-full w-full items-center justify-center overflow-hidden rounded-full bg-[radial-gradient(circle_at_35%_30%,var(--color-gengar-500),var(--color-gengar-800)_75%)]">
      <img src="/gengar-face.png" alt="" className="h-[78%] w-[78%] object-contain" draggable={false} />
    </span>
  </span>
);
