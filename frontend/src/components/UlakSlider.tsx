import { useEffect, useRef, useState } from "react";

// Vite'ın statik asset glob'u — src/assets/ulak-slider/ klasörüne yeni görsel
// eklendiğinde array otomatik güncellenir, kod değişikliği gerekmez.
const gorseller = Object.values(
  import.meta.glob<{ default: string }>("../assets/ulak-slider/*.png", { eager: true })
).map((m) => m.default);

const GECIS_SURESI_MS = 3000;

export default function UlakSlider() {
  const [aktifIndex, setAktifIndex] = useState(0);
  // setInterval kapanışının her tick'te en güncel index'i görmesi için ref
  // kullanılıyor — interval'i her state değişiminde yeniden kurmadan.
  const aktifIndexRef = useRef(0);
  aktifIndexRef.current = aktifIndex;

  useEffect(() => {
    if (gorseller.length < 2) return;

    const interval = setInterval(() => {
      let sonraki: number;
      do {
        sonraki = Math.floor(Math.random() * gorseller.length);
      } while (sonraki === aktifIndexRef.current);
      setAktifIndex(sonraki);
    }, GECIS_SURESI_MS);

    return () => clearInterval(interval);
  }, []);

  if (gorseller.length === 0) return null;

  return (
    <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-slate-900">
      {gorseller.map((src, i) => (
        <img
          key={src}
          src={src}
          alt=""
          aria-hidden={i !== aktifIndex}
          className="absolute inset-0 w-full h-full object-cover transition-opacity duration-1000 ease-in-out will-change-[opacity]"
          style={{ opacity: i === aktifIndex ? 1 : 0 }}
        />
      ))}
    </div>
  );
}
