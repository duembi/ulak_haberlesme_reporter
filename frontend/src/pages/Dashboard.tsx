import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X, ExternalLink, Network } from "lucide-react";
import { statsApi, type Istatistik, type HaberOzet, type RakipKartHaberi, type LinkedInGonderi } from "@/lib/api";
import { formatTarih } from "@/lib/utils";
import UlakSlider from "@/components/UlakSlider";

// ── LinkedIn paylaşımları popup'ı (ULAK + rakip kartları ortak) ─────────────────

function LinkedInPostlarPopup({ firma, baslik, onKapat }: { firma: string; baslik: string; onKapat: () => void }) {
  const { data = [], isLoading, isError } = useQuery<LinkedInGonderi[]>({
    queryKey: ["dashboard-linkedin", firma],
    queryFn: () => statsApi.linkedin(firma),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onKapat}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Network size={17} className="text-[#0A66C2]" /> {baslik} — LinkedIn
            </h2>
            <p className="text-slate-500 text-sm mt-0.5">
              {isLoading ? "Tag'ler ve paylaşımlar toplanıyor…" : isError ? "Bulunamadı" : `${data.length} paylaşım`}
            </p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-2.5">
          {isLoading ? (
            [...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-50 rounded-xl animate-pulse" />
            ))
          ) : isError ? (
            <p className="text-sm text-red-500 text-center py-10">Paylaşımlar getirilemedi.</p>
          ) : data.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-10">Paylaşım bulunamadı.</p>
          ) : (
            data.map((p, i) => (
              <a
                key={i}
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start justify-between gap-3 p-3.5 rounded-xl border border-slate-100 hover:border-brand-300 hover:bg-brand-50/50 transition-colors group"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 group-hover:text-brand-700 line-clamp-2">
                    {p.baslik}
                  </p>
                  {p.ozet && <p className="text-xs text-slate-400 line-clamp-2 mt-1">{p.ozet}</p>}
                  {p.tag && (
                    <span className="inline-block mt-1.5 text-xs text-[#0A66C2] bg-[#0A66C2]/10 px-1.5 py-0.5 rounded-full font-medium">
                      {p.tag}
                    </span>
                  )}
                </div>
                <ExternalLink size={14} className="text-slate-300 group-hover:text-brand-500 shrink-0 mt-1" />
              </a>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ── ULAK kartı + dönem popup'ı ──────────────────────────────────────────────────

const DONEMLER = [
  { key: "bugun", label: "Bugün", gun: 1 },
  { key: "hafta", label: "Bu Hafta", gun: 7 },
  { key: "ay", label: "Bu Ay", gun: 30 },
  { key: "sene", label: "Bu Sene", gun: 365 },
] as const;

type Donem = (typeof DONEMLER)[number];

function HaberPopup({ donem, onKapat }: { donem: Donem; onKapat: () => void }) {
  const { data = [], isLoading } = useQuery<HaberOzet[]>({
    queryKey: ["dashboard-haberler", donem.gun],
    queryFn: () => statsApi.haberler(donem.gun),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onKapat}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-slate-900">ULAK — {donem.label}</h2>
            <p className="text-slate-500 text-sm mt-0.5">
              {isLoading ? "Yükleniyor…" : `${data.length} haber`}
            </p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-2.5">
          {isLoading ? (
            [...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-50 rounded-xl animate-pulse" />
            ))
          ) : data.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-10">Bu dönemde haber bulunamadı.</p>
          ) : (
            data.map((h) => (
              <a
                key={h.id}
                href={h.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start justify-between gap-3 p-3.5 rounded-xl border border-slate-100 hover:border-brand-300 hover:bg-brand-50/50 transition-colors group"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 group-hover:text-brand-700 line-clamp-2">
                    {h.baslik}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-slate-400 flex-wrap">
                    {h.kaynak && <span>{h.kaynak}</span>}
                    {h.tarih && <span>· {formatTarih(h.tarih)}</span>}
                  </div>
                </div>
                <ExternalLink size={14} className="text-slate-300 group-hover:text-brand-500 shrink-0 mt-1" />
              </a>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function UlakKarti() {
  const [acikDonem, setAcikDonem] = useState<Donem | null>(null);
  const [linkedinAcik, setLinkedinAcik] = useState(false);

  const { data: sayilar } = useQuery<Record<string, number>>({
    queryKey: ["ulak-haber-sayilari"],
    queryFn: statsApi.haberSayilari,
    staleTime: 60_000,
  });

  return (
    <div className="card p-6 grid grid-cols-12 gap-6" style={{ borderTop: "3px solid #5CCAE8" }}>
      <div className="col-span-12 lg:col-span-7">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center shrink-0 overflow-hidden">
            <img src="/logo.svg" alt="" className="w-full h-full object-contain p-1" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold" style={{ color: "#0B8FB0" }}>ULAK</h2>
            <p className="text-xs text-slate-400">Dönem seçin, o dönemin haberlerini görün</p>
          </div>
          <button
            onClick={() => setLinkedinAcik(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-[#0A66C2]/30 text-[#0A66C2] bg-[#0A66C2]/5 hover:bg-[#0A66C2]/10 transition-colors shrink-0"
          >
            <Network size={14} /> LinkedIn
          </button>
        </div>
        <div className="space-y-2">
          {DONEMLER.map((d) => (
            <button
              key={d.key}
              onClick={() => setAcikDonem(d)}
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-brand-50 hover:border-brand-300 hover:text-brand-700 transition-colors"
            >
              <span className="text-sm font-medium">{d.label}</span>
              <span className="text-sm font-semibold text-slate-800">{sayilar?.[String(d.gun)] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="col-span-12 lg:col-span-5">
        <UlakSlider />
      </div>

      {acikDonem && <HaberPopup donem={acikDonem} onKapat={() => setAcikDonem(null)} />}
      {linkedinAcik && (
        <LinkedInPostlarPopup firma="ULAK" baslik="ULAK" onKapat={() => setLinkedinAcik(false)} />
      )}
    </div>
  );
}

// ── Rakip firma kartları (ASELSAN, SSB, SSTEK, Havelsan) ────────────────────────

const RAKIP_KART_DONEMLER = [
  { key: "1", gun: 1, label: "Bugün" },
  { key: "7", gun: 7, label: "Bu Hafta" },
  { key: "30", gun: 30, label: "Bu Ay" },
] as const;

type RakipDonem = (typeof RAKIP_KART_DONEMLER)[number];

function RakipHaberPopup({ firma, donem, onKapat }: { firma: string; donem: RakipDonem; onKapat: () => void }) {
  const { data = [], isLoading } = useQuery<RakipKartHaberi[]>({
    queryKey: ["rakip-haberler", firma, donem.gun],
    queryFn: () => statsApi.rakipHaberler(firma, donem.gun),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onKapat}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-slate-900">{firma} — {donem.label}</h2>
            <p className="text-slate-500 text-sm mt-0.5">
              {isLoading ? "Yükleniyor…" : `${data.length} haber`}
            </p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-2.5">
          {isLoading ? (
            [...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-50 rounded-xl animate-pulse" />
            ))
          ) : data.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-10">Bu dönemde haber bulunamadı.</p>
          ) : (
            data.map((h) => (
              <a
                key={h.url}
                href={h.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start justify-between gap-3 p-3.5 rounded-xl border border-slate-100 hover:border-brand-300 hover:bg-brand-50/50 transition-colors group"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 group-hover:text-brand-700 line-clamp-2">
                    {h.baslik}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-slate-400 flex-wrap">
                    {h.kaynak && <span>{h.kaynak}</span>}
                    {h.tarih && <span>· {formatTarih(h.tarih)}</span>}
                  </div>
                </div>
                <ExternalLink size={14} className="text-slate-300 group-hover:text-brand-500 shrink-0 mt-1" />
              </a>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

const RAKIP_MARKA: Record<string, { renk: string; logo: string }> = {
  ASELSAN:  { renk: "#013088", logo: "/rakip-logos/aselsan.png" },
  SSB:      { renk: "#E31513", logo: "/rakip-logos/ssb.png" },
  SSTEK:    { renk: "#0951F8", logo: "/rakip-logos/sstek.png" },
  Havelsan: { renk: "#B80A2E", logo: "/rakip-logos/havelsan.png" },
};

function RakipKarti({ ad, sayilar }: { ad: string; sayilar?: Record<string, number> }) {
  const [acikDonem, setAcikDonem] = useState<RakipDonem | null>(null);
  const [linkedinAcik, setLinkedinAcik] = useState(false);
  const marka = RAKIP_MARKA[ad];

  return (
    <div className="card p-5" style={{ borderTop: `3px solid ${marka?.renk ?? "#E2E8F0"}` }}>
      <div className="flex items-center gap-2.5 mb-3">
        {marka && (
          <div className="w-8 h-8 rounded-lg bg-white border border-slate-100 flex items-center justify-center shrink-0 overflow-hidden">
            <img src={marka.logo} alt="" className="w-full h-full object-contain p-1" />
          </div>
        )}
        <h3 className="text-sm font-semibold" style={{ color: marka?.renk ?? "#0F172A" }}>{ad}</h3>
      </div>
      <button
        onClick={() => setLinkedinAcik(true)}
        className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 mb-2 rounded-lg text-xs font-medium border border-[#0A66C2]/30 text-[#0A66C2] bg-[#0A66C2]/5 hover:bg-[#0A66C2]/10 transition-colors"
      >
        <Network size={14} /> LinkedIn
      </button>
      <div className="space-y-2">
        {RAKIP_KART_DONEMLER.map((d) => (
          <button
            key={d.key}
            onClick={() => setAcikDonem(d)}
            className="w-full flex items-center justify-between px-3.5 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-brand-50 hover:border-brand-300 hover:text-brand-700 transition-colors"
          >
            <span className="text-sm font-medium">{d.label}</span>
            <span className="text-sm font-semibold text-slate-800">{sayilar?.[d.key] ?? 0}</span>
          </button>
        ))}
      </div>
      {acikDonem && <RakipHaberPopup firma={ad} donem={acikDonem} onKapat={() => setAcikDonem(null)} />}
      {linkedinAcik && (
        <LinkedInPostlarPopup firma={ad} baslik={ad} onKapat={() => setLinkedinAcik(false)} />
      )}
    </div>
  );
}

function RakipKartlari() {
  const { data, isLoading } = useQuery<Record<string, Record<string, number>>>({
    queryKey: ["rakip-kartlar"],
    queryFn: statsApi.rakipKartlar,
    staleTime: 5 * 60_000,
  });

  const firmalar = ["ASELSAN", "SSB", "SSTEK", "Havelsan"];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {isLoading
        ? firmalar.map((ad) => <div key={ad} className="card h-36 bg-slate-50 animate-pulse" />)
        : firmalar.map((ad) => <RakipKarti key={ad} ad={ad} sayilar={data?.[ad]} />)}
    </div>
  );
}

// ── Ana bileşen ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery<Istatistik>({
    queryKey: ["stats"],
    queryFn: statsApi.al,
    refetchInterval: 30_000,
  });

  if (isLoading) return <Skeleton />;
  if (isError || !data) return <ErrorState />;

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">Son 7 günün medya özeti</p>
      </div>

      {/* ULAK kartı — dönem bazlı haber popup'ı */}
      <UlakKarti />

      {/* Rakip firma kartları */}
      <RakipKartlari />
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-slate-200 rounded-lg" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <div key={i} className="card h-28 bg-slate-50" />)}
      </div>
      <div className="card h-56 bg-slate-50" />
    </div>
  );
}

function ErrorState() {
  return (
    <div className="card p-12 text-center">
      <p className="text-slate-500 text-sm">API'ye bağlanılamadı. Giriş yapmanız gerekiyor olabilir.</p>
    </div>
  );
}
