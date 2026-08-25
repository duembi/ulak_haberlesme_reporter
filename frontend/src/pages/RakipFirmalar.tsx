import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2, Plus, Trash2, Pencil,
  ToggleLeft, ToggleRight, X, Check,
  Sparkles, Newspaper, ExternalLink, Network,
} from "lucide-react";
import { tenantRakipApi, type TenantRakip, type FirmaSonucu } from "@/lib/api";
import { cn, formatTarih } from "@/lib/utils";

// NOT: Bu sayfa tenant'a özel /tenant-competitors/ uçlarını kullanır — her yeni
// kurum boş bir listeyle başlar; rakipler yalnızca "Otomatik Bul" (LLM, tenant
// domaininden) veya manuel ekleme ile oluşur.

interface RakipForm {
  ad: string; bolge: string; sektor: string; aciklama: string;
}
const BOSH_FORM: RakipForm = { ad: "", bolge: "", sektor: "", aciklama: "" };

function RakipFormAlani({ label, value, onChange, placeholder, required = false, mono = false }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; required?: boolean; mono?: boolean;
}) {
  return (
    <div>
      <label className="label mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
      <input
        className={cn("input", mono && "font-mono text-sm")}
        value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      />
    </div>
  );
}

function RakipSatiri({ rakip, secili, onSecimDegistir, onToggle, onSil }: {
  rakip: TenantRakip; secili: boolean; onSecimDegistir: () => void;
  onToggle: () => void; onSil: () => void;
}) {
  const [duzenle, setDuzenle] = useState(false);
  const [form, setForm] = useState<RakipForm>({
    ad: rakip.ad, bolge: rakip.bolge, sektor: rakip.sektor, aciklama: rakip.aciklama,
  });
  const qc = useQueryClient();
  const set = (k: keyof RakipForm) => (v: string) => setForm(p => ({ ...p, [k]: v }));

  const kaydet = useMutation({
    mutationFn: () => tenantRakipApi.guncelle(rakip.id, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tenant-rakipler"] }); setDuzenle(false); },
  });

  return (
    <div className={cn("border rounded-xl overflow-hidden transition-colors",
      rakip.aktif ? "border-slate-200" : "border-slate-200 bg-slate-50 opacity-60",
    )}>
      <div className="flex items-center gap-3 px-4 py-3">
        <input
          type="checkbox"
          className="w-4 h-4 rounded accent-brand-600 shrink-0 cursor-pointer"
          checked={secili}
          onChange={onSecimDegistir}
        />
        <button onClick={onToggle} className="text-slate-400 hover:text-brand-600 transition-colors shrink-0">
          {rakip.aktif ? <ToggleRight size={20} className="text-brand-600" /> : <ToggleLeft size={20} />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-800">{rakip.ad}</span>
            {rakip.bolge && <span className="text-xs text-slate-400">{rakip.bolge}</span>}
            {rakip.sektor && (
              <span className="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-medium">{rakip.sektor}</span>
            )}
            {rakip.ai_onerisi && (
              <span className="text-xs bg-brand-100 text-brand-700 px-1.5 py-0.5 rounded font-medium">AI</span>
            )}
          </div>
          {!duzenle && rakip.aciklama && <p className="text-xs text-slate-400 truncate mt-0.5">{rakip.aciklama}</p>}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => setDuzenle(d => !d)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors">
            {duzenle ? <X size={15} /> : <Pencil size={15} />}
          </button>
          <button onClick={onSil}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors">
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {duzenle && (
        <div className="border-t border-slate-200 p-4 bg-slate-50 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <RakipFormAlani label="Ad" value={form.ad} onChange={set("ad")} required />
            <RakipFormAlani label="Bölge" value={form.bolge} onChange={set("bolge")} />
          </div>
          <RakipFormAlani label="Sektör" value={form.sektor} onChange={set("sektor")}
            placeholder="örn: Uydu haberleşmesi" />
          <RakipFormAlani label="Açıklama" value={form.aciklama} onChange={set("aciklama")} />
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={() => setDuzenle(false)} className="btn-ghost flex items-center gap-1.5 text-sm">
              <X size={14} /> İptal
            </button>
            <button onClick={() => kaydet.mutate()}
              disabled={kaydet.isPending || !form.ad}
              className="btn-primary flex items-center gap-1.5 text-sm disabled:opacity-50">
              <Check size={14} /> Kaydet
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Toplanan haberler + LinkedIn popup'ı ─────────────────────────────────────

function RakipHaberSonucPopup({ veri, onKapat }: {
  veri: Record<string, FirmaSonucu>; onKapat: () => void;
}) {
  const firmalar = Object.keys(veri);
  const toplamHaber = firmalar.reduce((t, f) => t + veri[f].haberler.length, 0);
  const toplamLinkedin = firmalar.reduce((t, f) => t + veri[f].linkedin.length, 0);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onKapat}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Toplanan İçerikler</h2>
            <p className="text-slate-500 text-sm mt-0.5">
              {firmalar.length} firma · {toplamHaber} haber · {toplamLinkedin} LinkedIn paylaşımı
            </p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-6">
          {firmalar.map(firma => (
            <section key={firma} className="space-y-4">
              <h3 className="text-sm font-semibold text-slate-800 px-1">{firma}</h3>

              <div className="space-y-2">
                <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                  <Newspaper size={12} /> Haberler — {veri[firma].haberler.length}
                </h4>
                {veri[firma].haberler.length === 0 ? (
                  <p className="text-xs text-slate-400 px-1">Bu dönemde haber bulunamadı.</p>
                ) : (
                  veri[firma].haberler.map((h, i) => (
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
                <h4 className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                  <Network size={12} className="text-[#0A66C2]" /> LinkedIn — {veri[firma].linkedin.length}
                </h4>
                {veri[firma].linkedin.length === 0 ? (
                  <p className="text-xs text-slate-400 px-1">LinkedIn'de paylaşım bulunamadı.</p>
                ) : (
                  veri[firma].linkedin.map((p, i) => (
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
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Ana sayfa ─────────────────────────────────────────────────────────────────

export default function RakipFirmalar() {
  const qc = useQueryClient();
  const [yeniAcik, setYeniAcik] = useState(false);
  const [yeniForm, setYeniForm] = useState<RakipForm>(BOSH_FORM);
  const [silinecek, setSilinecek] = useState<number | null>(null);
  const [analizHata, setAnalizHata] = useState("");
  const [analizBekliyor, setAnalizBekliyor] = useState(false);
  const [seciliIdler, setSeciliIdler] = useState<Set<number>>(new Set());
  const [sonuc, setSonuc] = useState<Record<string, FirmaSonucu> | null>(null);

  const { data: rakipler = [], isLoading } = useQuery<TenantRakip[]>({
    queryKey: ["tenant-rakipler"],
    queryFn: () => tenantRakipApi.listele(false),
  });

  const toggle = useMutation({
    mutationFn: (r: TenantRakip) => tenantRakipApi.guncelle(r.id, { aktif: !r.aktif }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tenant-rakipler"] }),
  });

  const ekle = useMutation({
    mutationFn: () => tenantRakipApi.ekle(yeniForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenant-rakipler"] });
      setYeniAcik(false);
      setYeniForm(BOSH_FORM);
    },
  });

  const sil = useMutation({
    mutationFn: (id: number) => tenantRakipApi.sil(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tenant-rakipler"] }); setSilinecek(null); },
  });

  const analiz = useMutation({
    mutationFn: () => tenantRakipApi.analizBaslat(),
    onSuccess: () => {
      setAnalizHata("");
      setAnalizBekliyor(true);
      // Arka planda üretiliyor — birkaç saniye sonra listeyi tazele
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["tenant-rakipler"] });
        setAnalizBekliyor(false);
      }, 8000);
    },
    onError: (e: any) => {
      setAnalizHata(e.response?.data?.detail ?? "LLM analizi başarısız oldu");
      setAnalizBekliyor(false);
    },
  });

  const seciliRakipler = rakipler.filter(r => seciliIdler.has(r.id));

  const olustur = useMutation({
    mutationFn: () => tenantRakipApi.haberler(seciliRakipler.map(r => r.ad), 7),
    onSuccess: (veri) => setSonuc(veri),
  });

  const secimDegistir = (id: number) => {
    setSeciliIdler(prev => {
      const yeni = new Set(prev);
      if (yeni.has(id)) yeni.delete(id); else yeni.add(id);
      return yeni;
    });
  };

  const set = (k: keyof RakipForm) => (v: string) => setYeniForm(p => ({ ...p, [k]: v }));
  const aktifler = rakipler.filter(r => r.aktif);
  const pasifler = rakipler.filter(r => !r.aktif);

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Building2 size={22} className="text-brand-600" />
          <h1 className="text-2xl font-semibold text-slate-900">Rakip Firmalar</h1>
        </div>
        <p className="text-slate-500 text-sm">
          {aktifler.length} aktif · {pasifler.length} pasif
          {seciliIdler.size > 0 && ` · ${seciliIdler.size} seçili`}
        </p>
      </div>

      <div className="flex items-center justify-end gap-2 flex-wrap">
        <button
          onClick={() => olustur.mutate()}
          disabled={seciliIdler.size === 0 || olustur.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-brand-300 text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors disabled:opacity-50"
        >
          <Newspaper size={15} className={olustur.isPending ? "animate-pulse" : ""} />
          {olustur.isPending ? "Toplanıyor…" : `Oluştur${seciliIdler.size > 0 ? ` (${seciliIdler.size})` : ""}`}
        </button>
        <button
          onClick={() => analiz.mutate()}
          disabled={analiz.isPending || analizBekliyor}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-brand-300 text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors disabled:opacity-50"
        >
          <Sparkles size={15} className={(analiz.isPending || analizBekliyor) ? "animate-pulse" : ""} />
          {(analiz.isPending || analizBekliyor) ? "Analiz ediliyor…" : "Otomatik Bul"}
        </button>
        <button onClick={() => setYeniAcik(v => !v)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Yeni Rakip
        </button>
      </div>

      {olustur.isError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex items-center justify-between">
          <span>{(olustur.error as any)?.response?.data?.detail ?? "Haberler toplanamadı"}</span>
          <button onClick={() => olustur.reset()} className="ml-3 text-red-400 hover:text-red-600">
            <X size={14} />
          </button>
        </div>
      )}

      {analizHata && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex items-center justify-between">
          <span>{analizHata}</span>
          <button onClick={() => setAnalizHata("")} className="ml-3 text-red-400 hover:text-red-600">
            <X size={14} />
          </button>
        </div>
      )}

      {(analiz.isPending || analizBekliyor) && (
        <div className="rounded-lg bg-brand-50 border border-brand-200 px-4 py-3 text-sm text-brand-700">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin shrink-0" />
            E-posta uzantınızdan firma sektörü tespit ediliyor, rakipler LLM ile analiz ediliyor…
          </div>
        </div>
      )}

      {yeniAcik && (
        <div className="card p-5 border-brand-200 bg-brand-50 space-y-3">
          <h3 className="text-sm font-semibold text-brand-900">Yeni Rakip Ekle</h3>
          <div className="grid grid-cols-2 gap-3">
            <RakipFormAlani label="Ad" value={yeniForm.ad} onChange={set("ad")}
              placeholder="örn: OneWeb" required />
            <RakipFormAlani label="Bölge" value={yeniForm.bolge} onChange={set("bolge")}
              placeholder="örn: İngiltere" />
          </div>
          <RakipFormAlani label="Sektör" value={yeniForm.sektor} onChange={set("sektor")}
            placeholder="örn: LEO uydu interneti" />
          <RakipFormAlani label="Açıklama" value={yeniForm.aciklama} onChange={set("aciklama")}
            placeholder="Kısa açıklama (opsiyonel)" />
          {ekle.isError && (
            <p className="text-xs text-red-600">
              {(ekle.error as any)?.response?.data?.detail ?? "Bir hata oluştu"}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={() => setYeniAcik(false)} className="btn-ghost flex items-center gap-1.5 text-sm">
              <X size={14} /> İptal
            </button>
            <button onClick={() => ekle.mutate()}
              disabled={ekle.isPending || !yeniForm.ad.trim()}
              className="btn-primary flex items-center gap-1.5 text-sm disabled:opacity-50">
              <Plus size={14} /> Ekle
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-8 text-slate-400 text-sm">Yükleniyor…</div>
      ) : rakipler.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">
          Henüz rakip eklenmemiş. "Otomatik Bul" ile LLM önerisi alın ya da elle ekleyin.
        </div>
      ) : (
        <div className="space-y-6">
          {aktifler.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                Aktif — {aktifler.length} firma
              </h3>
              {aktifler.map(r => (
                <RakipSatiri key={r.id} rakip={r}
                  secili={seciliIdler.has(r.id)}
                  onSecimDegistir={() => secimDegistir(r.id)}
                  onToggle={() => toggle.mutate(r)}
                  onSil={() => setSilinecek(r.id)} />
              ))}
            </section>
          )}
          {pasifler.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide px-1">
                Pasif — {pasifler.length} firma
              </h3>
              {pasifler.map(r => (
                <RakipSatiri key={r.id} rakip={r}
                  secili={seciliIdler.has(r.id)}
                  onSecimDegistir={() => secimDegistir(r.id)}
                  onToggle={() => toggle.mutate(r)}
                  onSil={() => setSilinecek(r.id)} />
              ))}
            </section>
          )}
        </div>
      )}

      {silinecek !== null && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="card p-6 max-w-sm w-full space-y-4">
            <h3 className="text-base font-semibold text-slate-900">Rakibi sil?</h3>
            <p className="text-sm text-slate-500">
              Bu işlem geri alınamaz. Geçici olarak devre dışı bırakmak için toggle'ı kullanın.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setSilinecek(null)} className="btn-ghost text-sm">İptal</button>
              <button onClick={() => sil.mutate(silinecek)} disabled={sil.isPending}
                className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50">
                Evet, sil
              </button>
            </div>
          </div>
        </div>
      )}

      {sonuc && <RakipHaberSonucPopup veri={sonuc} onKapat={() => setSonuc(null)} />}
    </div>
  );
}
