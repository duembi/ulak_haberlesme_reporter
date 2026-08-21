import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2, Plus, Pencil, Trash2, X, Check,
  ToggleLeft, ToggleRight, ChevronUp,
} from "lucide-react";
import { http } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Rakip {
  id: number;
  ad: string;
  rss_sorgu: string;
  rss_dil: "tr" | "en";
  ticker: string | null;
  bolge: string;
  aciklama: string;
  aktif: boolean;
  eklendi_at: string;
}

interface RakipForm {
  ad: string;
  rss_sorgu: string;
  rss_dil: "tr" | "en";
  ticker: string;
  bolge: string;
  aciklama: string;
}

const BOSH_FORM: RakipForm = {
  ad: "", rss_sorgu: "", rss_dil: "en", ticker: "", bolge: "", aciklama: "",
};

// ── API ───────────────────────────────────────────────────────────────────────

const api = {
  listele: () => http.get<Rakip[]>("/competitors/").then(r => r.data),
  ekle:    (d: RakipForm) => http.post<Rakip>("/competitors/", d).then(r => r.data),
  guncelle:(id: number, d: Partial<RakipForm & { aktif: boolean }>) =>
    http.patch<Rakip>(`/competitors/${id}`, d).then(r => r.data),
  sil:     (id: number) => http.delete(`/competitors/${id}`),
};

// ── Alt bileşenler ────────────────────────────────────────────────────────────

function FormAlani({
  label, value, onChange, placeholder, required = false, mono = false,
}: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; required?: boolean; mono?: boolean;
}) {
  return (
    <div>
      <label className="label mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
      <input
        className={cn("input", mono && "font-mono text-sm")}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function RakipSatiri({
  rakip, onToggle, onSil,
}: {
  rakip: Rakip;
  onToggle: () => void;
  onSil: () => void;
}) {
  const [duzenle, setDuzenle] = useState(false);
  const [form, setForm] = useState<RakipForm>({
    ad: rakip.ad, rss_sorgu: rakip.rss_sorgu, rss_dil: rakip.rss_dil,
    ticker: rakip.ticker ?? "", bolge: rakip.bolge, aciklama: rakip.aciklama,
  });
  const qc = useQueryClient();

  const kaydet = useMutation({
    mutationFn: () => api.guncelle(rakip.id, {
      ...form, ticker: form.ticker.trim() || undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["rakipler"] }); setDuzenle(false); },
  });

  const set = (k: keyof RakipForm) => (v: string) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div className={cn(
      "border rounded-xl overflow-hidden transition-colors",
      rakip.aktif ? "border-slate-200" : "border-slate-200 bg-slate-50 opacity-60",
    )}>
      {/* Satır başlığı */}
      <div className="flex items-center gap-3 px-4 py-3">
        <button onClick={onToggle} className="text-slate-400 hover:text-brand-600 transition-colors shrink-0">
          {rakip.aktif
            ? <ToggleRight size={20} className="text-brand-600" />
            : <ToggleLeft size={20} />
          }
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-800">{rakip.ad}</span>
            <span className="text-xs text-slate-400">{rakip.bolge}</span>
            {rakip.ticker && (
              <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-mono">
                {rakip.ticker}
              </span>
            )}
            <span className={cn(
              "text-xs px-1.5 py-0.5 rounded font-medium",
              rakip.rss_dil === "tr" ? "bg-red-100 text-red-600" : "bg-blue-100 text-blue-600",
            )}>
              {rakip.rss_dil.toUpperCase()}
            </span>
          </div>
          {!duzenle && (
            <p className="text-xs text-slate-400 truncate mt-0.5">{rakip.rss_sorgu}</p>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => setDuzenle(d => !d)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
          >
            {duzenle ? <ChevronUp size={15} /> : <Pencil size={15} />}
          </button>
          <button
            onClick={onSil}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {/* Düzenleme formu */}
      {duzenle && (
        <div className="border-t border-slate-200 p-4 bg-slate-50 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <FormAlani label="Ad" value={form.ad} onChange={set("ad")} required />
            <FormAlani label="Bölge" value={form.bolge} onChange={set("bolge")} required />
          </div>
          <FormAlani
            label="RSS Sorgusu" value={form.rss_sorgu} onChange={set("rss_sorgu")}
            placeholder="örn: Eutelsat satellite news" required mono
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label mb-1">Dil</label>
              <div className="flex gap-2">
                {(["tr", "en"] as const).map(dil => (
                  <button
                    key={dil}
                    onClick={() => setForm(p => ({ ...p, rss_dil: dil }))}
                    className={cn(
                      "flex-1 py-2 rounded-lg text-sm font-medium border transition-colors",
                      form.rss_dil === dil
                        ? "bg-brand-600 text-white border-brand-600"
                        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50",
                    )}
                  >
                    {dil.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            <FormAlani label="Borsa Kodu" value={form.ticker} onChange={set("ticker")}
              placeholder="TCELL.IS (opsiyonel)" mono />
          </div>
          <FormAlani label="Açıklama" value={form.aciklama} onChange={set("aciklama")} />

          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={() => setDuzenle(false)}
              className="btn-ghost flex items-center gap-1.5 text-sm"
            >
              <X size={14} /> İptal
            </button>
            <button
              onClick={() => kaydet.mutate()}
              disabled={kaydet.isPending || !form.ad || !form.rss_sorgu || !form.bolge}
              className="btn-primary flex items-center gap-1.5 text-sm disabled:opacity-50"
            >
              <Check size={14} /> Kaydet
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function YeniRakipFormu({ onKapat }: { onKapat: () => void }) {
  const [form, setForm] = useState<RakipForm>(BOSH_FORM);
  const qc = useQueryClient();

  const ekle = useMutation({
    mutationFn: () => api.ekle({ ...form, ticker: form.ticker.trim() || "" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["rakipler"] }); onKapat(); },
  });

  const set = (k: keyof RakipForm) => (v: string) => setForm(p => ({ ...p, [k]: v }));
  const gecerli = form.ad.trim() && form.rss_sorgu.trim() && form.bolge.trim();

  return (
    <div className="card p-5 border-brand-200 bg-brand-50 space-y-3">
      <h3 className="text-sm font-semibold text-brand-900">Yeni Rakip Ekle</h3>

      <div className="grid grid-cols-2 gap-3">
        <FormAlani label="Ad" value={form.ad} onChange={set("ad")}
          placeholder="örn: OneWeb" required />
        <FormAlani label="Bölge" value={form.bolge} onChange={set("bolge")}
          placeholder="örn: İngiltere" required />
      </div>
      <FormAlani
        label="RSS Sorgusu" value={form.rss_sorgu} onChange={set("rss_sorgu")}
        placeholder="örn: OneWeb satellite internet LEO" required mono
      />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label mb-1">Dil</label>
          <div className="flex gap-2">
            {(["tr", "en"] as const).map(dil => (
              <button
                key={dil}
                onClick={() => setForm(p => ({ ...p, rss_dil: dil }))}
                className={cn(
                  "flex-1 py-2 rounded-lg text-sm font-medium border transition-colors",
                  form.rss_dil === dil
                    ? "bg-brand-600 text-white border-brand-600"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50",
                )}
              >
                {dil.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <FormAlani label="Borsa Kodu" value={form.ticker} onChange={set("ticker")}
          placeholder="örn: ONEW.L (opsiyonel)" mono />
      </div>
      <FormAlani label="Açıklama" value={form.aciklama} onChange={set("aciklama")}
        placeholder="Kısa açıklama (opsiyonel)" />

      {ekle.isError && (
        <p className="text-xs text-red-600">
          {(ekle.error as any)?.response?.data?.detail ?? "Bir hata oluştu"}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <button onClick={onKapat} className="btn-ghost flex items-center gap-1.5 text-sm">
          <X size={14} /> İptal
        </button>
        <button
          onClick={() => ekle.mutate()}
          disabled={ekle.isPending || !gecerli}
          className="btn-primary flex items-center gap-1.5 text-sm disabled:opacity-50"
        >
          <Plus size={14} /> Ekle
        </button>
      </div>
    </div>
  );
}

// ── Ana sayfa ─────────────────────────────────────────────────────────────────

export default function Competitors() {
  const qc = useQueryClient();
  const [yeniAcik, setYeniAcik] = useState(false);
  const [silinecek, setSilinecek] = useState<number | null>(null);

  const { data: rakipler = [], isLoading } = useQuery<Rakip[]>({
    queryKey: ["rakipler"],
    queryFn: api.listele,
  });

  const toggle = useMutation({
    mutationFn: (r: Rakip) => api.guncelle(r.id, { aktif: !r.aktif }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rakipler"] }),
  });

  const sil = useMutation({
    mutationFn: (id: number) => api.sil(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["rakipler"] }); setSilinecek(null); },
  });

  const aktifler   = rakipler.filter(r => r.aktif);
  const pasifler   = rakipler.filter(r => !r.aktif);
  const borsalilar = aktifler.filter(r => r.ticker).length;
  const sirali     = [...rakipler].sort((a, b) => a.id - b.id);

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Building2 size={22} className="text-brand-600" />
            <h1 className="text-2xl font-semibold text-slate-900">Rakip Firmalar</h1>
          </div>
          <p className="text-slate-500 text-sm">
            Rakip takibini yönetin. Aktif firmalar raporda yer alır.
          </p>
        </div>
        <button
          onClick={() => setYeniAcik(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={16} /> Yeni Rakip
        </button>
      </div>

      {/* Özet */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Toplam",  deger: rakipler.length,  renk: "text-slate-700" },
          { label: "Aktif",   deger: aktifler.length,  renk: "text-green-700" },
          { label: "Borsalı", deger: borsalilar,       renk: "text-amber-700" },
        ].map(({ label, deger, renk }) => (
          <div key={label} className="card p-4 text-center">
            <p className={cn("text-2xl font-bold", renk)}>{deger}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Yeni rakip formu */}
      {yeniAcik && <YeniRakipFormu onKapat={() => setYeniAcik(false)} />}

      {/* Liste */}
      {isLoading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Yükleniyor…</div>
      ) : (
        <div className="space-y-2">
          {sirali.map(r => (
            <RakipSatiri
              key={r.id}
              rakip={r}
              onToggle={() => toggle.mutate(r)}
              onSil={() => setSilinecek(r.id)}
            />
          ))}
        </div>
      )}

      {/* Silme onay modalı */}
      {silinecek !== null && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="card p-6 max-w-sm w-full space-y-4">
            <h3 className="text-base font-semibold text-slate-900">Rakibi sil?</h3>
            <p className="text-sm text-slate-500">
              Bu işlem geri alınamaz. Rakip DB'den kalıcı olarak silinir.
              Geçici olarak devre dışı bırakmak için sol taraftaki toggle'ı kullanın.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setSilinecek(null)} className="btn-ghost text-sm">
                İptal
              </button>
              <button
                onClick={() => sil.mutate(silinecek)}
                disabled={sil.isPending}
                className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              >
                Evet, sil
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
