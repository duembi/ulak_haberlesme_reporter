import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Users, Newspaper, X, ExternalLink, RefreshCw, AlertTriangle,
  Sparkles, Trash2, Network,
} from "lucide-react";
import { yonetimApi, type YonetimKisi, type FirmaSonucu } from "@/lib/api";
import { formatTarih } from "@/lib/utils";

// ── Kişi haberleri + LinkedIn popup'ı ────────────────────────────────────────

function KisiHaberPopup({ kisi, onKapat }: { kisi: YonetimKisi; onKapat: () => void }) {
  const { data, isLoading, isError } = useQuery<FirmaSonucu>({
    queryKey: ["yonetim-haberler", kisi.id],
    queryFn: () => yonetimApi.haberler(kisi.id),
  });

  const haberler = data?.haberler ?? [];
  const linkedin = data?.linkedin ?? [];

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
            <h2 className="text-base font-semibold text-slate-900">{kisi.ad_soyad}</h2>
            <p className="text-slate-500 text-sm mt-0.5">
              {isLoading
                ? "Aranıyor…"
                : isError
                ? "Bulunamadı"
                : `${haberler.length} haber · ${linkedin.length} LinkedIn paylaşımı`}
            </p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-5">
          {isLoading ? (
            [...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-50 rounded-xl animate-pulse" />
            ))
          ) : isError ? (
            <p className="text-sm text-red-500 text-center py-10">Getirilemedi.</p>
          ) : haberler.length === 0 && linkedin.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-10">
              Bu kişiyle ilgili güncel bir haber/gelişme bulunamadı.
            </p>
          ) : (
            <>
              <div className="space-y-2">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                  <Newspaper size={12} /> Haberler — {haberler.length}
                </h3>
                {haberler.length === 0 ? (
                  <p className="text-xs text-slate-400 px-1">Haber bulunamadı.</p>
                ) : (
                  haberler.map((h, i) => (
                    <a
                      key={i}
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start justify-between gap-3 p-3 rounded-xl border border-slate-100 hover:border-brand-300 hover:bg-brand-50/50 transition-colors group"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-800 group-hover:text-brand-700 line-clamp-2">
                          {h.baslik}
                        </p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-slate-400 flex-wrap">
                          {h.kaynak && <span>{h.kaynak}</span>}
                          {h.tarih && <span>· {formatTarih(h.tarih)}</span>}
                        </div>
                      </div>
                      <ExternalLink size={14} className="text-slate-300 group-hover:text-brand-500 shrink-0 mt-1" />
                    </a>
                  ))
                )}
              </div>

              <div className="space-y-2">
                <h3 className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                  <Network size={12} className="text-[#0A66C2]" /> LinkedIn — {linkedin.length}
                </h3>
                {linkedin.length === 0 ? (
                  <p className="text-xs text-slate-400 px-1">Paylaşım bulunamadı.</p>
                ) : (
                  linkedin.map((p, i) => (
                    <a
                      key={i}
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start justify-between gap-3 p-3 rounded-xl border border-slate-100 hover:border-brand-300 hover:bg-brand-50/50 transition-colors group"
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Kişi kartı (resmi Kurul/Yönetim — fotoğraflı) ────────────────────────────

function KisiKarti({ kisi, yeniMi }: { kisi: YonetimKisi; yeniMi: boolean }) {
  const [haberAcik, setHaberAcik] = useState(false);

  return (
    <div className="card overflow-hidden relative">
      {yeniMi && (
        <span className="absolute top-2 right-2 z-10 text-[10px] font-semibold uppercase tracking-wide bg-brand-600 text-white px-2 py-0.5 rounded-full">
          Değişiklik
        </span>
      )}
      <div className="aspect-square w-full bg-slate-100 overflow-hidden">
        {kisi.foto_url ? (
          <img src={kisi.foto_url} alt={kisi.ad_soyad} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-300">
            <Users size={32} />
          </div>
        )}
      </div>
      <div className="p-4 space-y-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{kisi.ad_soyad}</p>
          <p className="text-xs text-slate-500 mt-0.5">{kisi.unvan}</p>
        </div>
        <button
          onClick={() => setHaberAcik(true)}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-brand-300 text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors"
        >
          <Newspaper size={13} /> Haberler
        </button>
      </div>
      {haberAcik && <KisiHaberPopup kisi={kisi} onKapat={() => setHaberAcik(false)} />}
    </div>
  );
}

// ── Üst kademe kartı (fotoğrafsız, LinkedIn keşfi/manuel — silinebilir) ──────

function UstKademeKarti({ kisi, yeniMi }: { kisi: YonetimKisi; yeniMi: boolean }) {
  const [haberAcik, setHaberAcik] = useState(false);
  const qc = useQueryClient();

  const sil = useMutation({
    mutationFn: () => yonetimApi.ustKademeSil(kisi.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["yonetim-kisiler"] }),
  });

  return (
    <div className="card p-4 relative">
      {yeniMi && (
        <span className="absolute top-2 right-2 z-10 text-[10px] font-semibold uppercase tracking-wide bg-brand-600 text-white px-2 py-0.5 rounded-full">
          Değişiklik
        </span>
      )}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center shrink-0 text-slate-400 overflow-hidden">
          {kisi.foto_url ? (
            <img src={kisi.foto_url} alt={kisi.ad_soyad} className="w-full h-full object-cover" />
          ) : (
            <Users size={18} />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-slate-900 truncate">{kisi.ad_soyad}</p>
          <p className="text-xs text-slate-500 truncate">{kisi.unvan}</p>
        </div>
        {kisi.linkedin_url && (
          <a
            href={kisi.linkedin_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg text-[#0A66C2] hover:bg-[#0A66C2]/10 transition-colors shrink-0"
            title="LinkedIn profili"
          >
            <Network size={15} />
          </a>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setHaberAcik(true)}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-brand-300 text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors"
        >
          <Newspaper size={13} /> Haberler
        </button>
        <button
          onClick={() => { if (confirm(`${kisi.ad_soyad} listeden kaldırılsın mı?`)) sil.mutate(); }}
          className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
          title="Kaldır"
        >
          <Trash2 size={15} />
        </button>
      </div>
      {haberAcik && <KisiHaberPopup kisi={kisi} onKapat={() => setHaberAcik(false)} />}
    </div>
  );
}

// ── Ana sayfa ─────────────────────────────────────────────────────────────────

export default function YonetimKurulu() {
  const qc = useQueryClient();

  const { data: kisiler = [], isLoading } = useQuery<YonetimKisi[]>({
    queryKey: ["yonetim-kisiler"],
    queryFn: yonetimApi.listele,
  });

  const { data: degisiklikler = [] } = useQuery({
    queryKey: ["yonetim-degisiklikler"],
    queryFn: yonetimApi.degisiklikler,
  });

  const senkronize = useMutation({
    mutationFn: yonetimApi.senkronize,
    onSuccess: (veri) => {
      qc.setQueryData(["yonetim-kisiler"], veri);
      qc.invalidateQueries({ queryKey: ["yonetim-degisiklikler"] });
    },
  });

  const ustKademeKesif = useMutation({
    mutationFn: yonetimApi.ustKademeKesif,
    onSuccess: (veri) => {
      qc.setQueryData(["yonetim-kisiler"], veri);
      qc.invalidateQueries({ queryKey: ["yonetim-degisiklikler"] });
    },
  });

  const sonDegisenIsimler = new Set(
    degisiklikler
      .filter(d => {
        const saatFarki = (Date.now() - new Date(d.tarih).getTime()) / 3_600_000;
        return saatFarki < 24;
      })
      .map(d => d.ad_soyad)
  );

  const kurul = kisiler.filter(k => k.grup === "kurul");
  const yonetim = kisiler.filter(k => k.grup === "yonetim");
  const ustKademe = kisiler.filter(k => k.grup === "ust_kademe");

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Users size={22} className="text-brand-600" />
            <h1 className="text-2xl font-semibold text-slate-900">Yönetim Kurulu</h1>
          </div>
          <p className="text-slate-500 text-sm">
            ulakhaberlesme.com.tr resmi sayfalarıyla senkronize
          </p>
        </div>
        <button
          onClick={() => senkronize.mutate()}
          disabled={senkronize.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 text-slate-600 bg-white hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={15} className={senkronize.isPending ? "animate-spin" : ""} />
          {senkronize.isPending ? "Taranıyor…" : "Yenile"}
        </button>
      </div>

      {sonDegisenIsimler.size > 0 && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800 flex items-start gap-2">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          <span>
            Son 24 saatte değişiklik tespit edildi: {[...sonDegisenIsimler].join(", ")}
          </span>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-8 text-slate-400 text-sm">Yükleniyor…</div>
      ) : (
        <>
          <section className="space-y-3">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
              Yönetim Kurulu — {kurul.length} kişi
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {kurul.map(k => (
                <KisiKarti key={k.id} kisi={k} yeniMi={sonDegisenIsimler.has(k.ad_soyad)} />
              ))}
            </div>
          </section>

          {yonetim.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                Yönetim — {yonetim.length} kişi
              </h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                {yonetim.map(k => (
                  <KisiKarti key={k.id} kisi={k} yeniMi={sonDegisenIsimler.has(k.ad_soyad)} />
                ))}
              </div>
            </section>
          )}

          <section className="space-y-3 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between pt-3">
              <div>
                <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                  Üst Kademe Çalışanlar — {ustKademe.length} kişi
                </h2>
                <p className="text-xs text-slate-400 px-1 mt-0.5">
                  LinkedIn'de Direktör/Müdür unvanlı çalışanlar — LLM ile keşfedilir
                </p>
              </div>
              <button
                onClick={() => ustKademeKesif.mutate()}
                disabled={ustKademeKesif.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-brand-300 text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors disabled:opacity-50"
              >
                <Sparkles size={15} className={ustKademeKesif.isPending ? "animate-pulse" : ""} />
                {ustKademeKesif.isPending ? "LinkedIn'de aranıyor…" : "LinkedIn'de Ara"}
              </button>
            </div>

            {ustKademeKesif.isError && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                Arama başarısız oldu, lütfen tekrar deneyin.
              </div>
            )}

            {ustKademe.length === 0 ? (
              <p className="text-sm text-slate-400 px-1 py-4">
                Henüz üst kademe çalışan eklenmedi. "LinkedIn'de Ara" ile otomatik keşfedin.
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {ustKademe.map(k => (
                  <UstKademeKarti key={k.id} kisi={k} yeniMi={sonDegisenIsimler.has(k.ad_soyad)} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
