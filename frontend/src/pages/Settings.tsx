import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings2, Plus, Trash2, CheckCircle2, Eye, EyeOff,
  Power, PowerOff, CheckCircle, Pencil,
  ToggleLeft, ToggleRight, X, Check,
  Network, Sparkles,
} from "lucide-react";
import { llmConfigApi, mailApi, tenantRakipApi, http, type LLMConfig, type Alici, type AliciOlustur, type TenantRakip } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatTarih } from "@/lib/utils";

type Tab = "llm" | "rakip" | "mail" | "linkedin";

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic (Claude)",
  openai:    "OpenAI",
  gemini:    "Google Gemini",
  custom:    "Özel (OpenAI uyumlu)",
};

// ── LLM Config Tab ────────────────────────────────────────────────────────────

function LLMKonfigurasyonu() {
  const qc = useQueryClient();
  const [formAcik, setFormAcik] = useState(false);
  const [apiKeyGoster, setApiKeyGoster] = useState(false);
  const [form, setForm] = useState({
    provider_name: "openai", model_name: "", api_key: "", base_url: "",
  });

  const { data: configs = [], isLoading } = useQuery<LLMConfig[]>({
    queryKey: ["llm-configs"],
    queryFn: llmConfigApi.listele,
  });

  const { data: aktif } = useQuery({
    queryKey: ["llm-configs", "active"],
    queryFn: llmConfigApi.aktifAl,
  });

  const ekle = useMutation({
    mutationFn: () => llmConfigApi.ekle({
      provider_name: form.provider_name,
      model_name: form.model_name,
      api_key: form.api_key,
      base_url: form.base_url || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llm-configs"] });
      setFormAcik(false);
      setForm({ provider_name: "openai", model_name: "", api_key: "", base_url: "" });
    },
  });

  const aktifle = useMutation({
    mutationFn: llmConfigApi.aktifle,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-configs"] }),
  });

  const sil = useMutation({
    mutationFn: llmConfigApi.sil,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-configs"] }),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">LLM Konfigürasyonu</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {aktif?.aktif
              ? `Aktif: ${aktif.provider_name} — ${aktif.model_name}`
              : "Aktif konfigürasyon yok — sistem varsayılanı kullanılıyor"}
          </p>
        </div>
        <button onClick={() => setFormAcik(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Yeni Model Ekle
        </button>
      </div>

      {formAcik && (
        <div className="card p-5 border-brand-200 bg-brand-50 space-y-4">
          <h3 className="text-sm font-semibold text-brand-900">Yeni Model Ekle</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label mb-1">Provider</label>
              <select
                className="input"
                value={form.provider_name}
                onChange={e => setForm({ ...form, provider_name: e.target.value })}
              >
                {Object.entries(PROVIDER_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label mb-1">Model Adı</label>
              <input
                className="input font-mono text-sm"
                placeholder="gpt-4o / claude-sonnet-4-6"
                value={form.model_name}
                onChange={e => setForm({ ...form, model_name: e.target.value })}
              />
            </div>
          </div>
          {form.provider_name === "custom" && (
            <div>
              <label className="label mb-1">Base URL</label>
              <input
                className="input font-mono text-sm"
                placeholder="http://localhost:11434/v1"
                value={form.base_url}
                onChange={e => setForm({ ...form, base_url: e.target.value })}
              />
            </div>
          )}
          <div>
            <label className="label mb-1">API Key</label>
            <div className="relative">
              <input
                className="input pr-10 font-mono text-sm"
                type={apiKeyGoster ? "text" : "password"}
                placeholder="sk-... / Bearer ..."
                value={form.api_key}
                onChange={e => setForm({ ...form, api_key: e.target.value })}
              />
              <button
                type="button"
                onClick={() => setApiKeyGoster(g => !g)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {apiKeyGoster ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              API key AES-256 ile şifrelenip veritabanına kaydedilir.
            </p>
          </div>
          {ekle.isError && (
            <p className="text-xs text-red-600">
              {(ekle.error as any)?.response?.data?.detail ?? "Bir hata oluştu"}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button onClick={() => setFormAcik(false)} className="btn-ghost text-sm">İptal</button>
            <button
              onClick={() => ekle.mutate()}
              disabled={ekle.isPending || !form.model_name || !form.api_key}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {ekle.isPending ? "Kaydediliyor…" : "Kaydet"}
            </button>
          </div>
        </div>
      )}

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Yükleniyor…</div>
        ) : configs.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            Henüz model eklenmemiş. Sistem varsayılan AI'ı kullanıyor.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                {["Provider", "Model", "Durum", "Eklenme", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {configs.map(c => (
                <tr key={c.id} className="border-b border-slate-50 table-row-hover">
                  <td className="px-4 py-3">
                    <span className="badge bg-slate-100 text-slate-700">{PROVIDER_LABELS[c.provider_name] ?? c.provider_name}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{c.model_name}</td>
                  <td className="px-4 py-3">
                    {c.aktif
                      ? <span className="flex items-center gap-1.5 text-green-600 text-xs"><CheckCircle size={13} /> Aktif</span>
                      : <span className="text-slate-400 text-xs">Pasif</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{formatTarih(c.olusturuldu_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {!c.aktif && (
                        <button
                          title="Aktifleştir"
                          onClick={() => aktifle.mutate(c.id)}
                          className="p-1.5 rounded-lg hover:bg-green-50 text-slate-400 hover:text-green-600 transition-colors"
                        >
                          <CheckCircle2 size={15} />
                        </button>
                      )}
                      <button
                        title="Sil"
                        onClick={() => { if (confirm("Bu konfigürasyon silinsin mi?")) sil.mutate(c.id); }}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Mail Tab ──────────────────────────────────────────────────────────────────

type Rol = "yonetici" | "izleyici" | "teknik";

const ROL_BADGE: Record<Rol, string> = {
  yonetici: "bg-purple-100 text-purple-700",
  izleyici: "bg-blue-100 text-blue-700",
  teknik:   "bg-orange-100 text-orange-700",
};

const DEFAULT_FORM: AliciOlustur = {
  ad_soyad: "", email: "", rol: "izleyici", haftalik: true, kriz: true, hata: false,
};

function MailListesi() {
  const qc = useQueryClient();
  const [formAcik, setFormAcik] = useState(false);
  const [form, setForm] = useState<AliciOlustur>(DEFAULT_FORM);
  const [hata, setHata] = useState("");

  const { data: alicilar = [], isLoading } = useQuery<Alici[]>({
    queryKey: ["mail"],
    queryFn: mailApi.listele,
  });

  const ekle = useMutation({
    mutationFn: mailApi.ekle,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mail"] });
      setFormAcik(false);
      setForm(DEFAULT_FORM);
      setHata("");
    },
    onError: (e: any) => setHata(e.response?.data?.detail ?? "Bir hata oluştu"),
  });

  const toggle = useMutation({
    mutationFn: ({ email, aktif }: { email: string; aktif: boolean }) =>
      mailApi.guncelle(email, { aktif }),
    onSuccess: (updated) => {
      qc.setQueryData<Alici[]>(["mail"], (old = []) =>
        old.map(a => a.id === updated.id ? updated : a)
      );
    },
  });

  const sil = useMutation({
    mutationFn: mailApi.sil,
    onSuccess: (_, email) => {
      qc.setQueryData<Alici[]>(["mail"], (old = []) =>
        old.filter(a => a.email !== email)
      );
    },
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Mail Listesi</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {alicilar.filter(a => a.aktif).length} aktif alıcı
          </p>
        </div>
        <button onClick={() => setFormAcik(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Alıcı Ekle
        </button>
      </div>

      {formAcik && (
        <div className="card p-5 border-brand-200 bg-brand-50 space-y-4">
          <h3 className="text-sm font-semibold text-brand-900">Yeni Alıcı</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label mb-1">Ad Soyad</label>
              <input className="input" placeholder="Ahmet Yılmaz"
                value={form.ad_soyad} onChange={e => setForm({ ...form, ad_soyad: e.target.value })} />
            </div>
            <div>
              <label className="label mb-1">E-posta</label>
              <input className="input" type="email" placeholder="ahmet@kurum.com"
                value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="label mb-1">Rol</label>
            <select className="input" value={form.rol}
              onChange={e => setForm({ ...form, rol: e.target.value as Rol })}>
              <option value="yonetici">Yönetici — Haftalık + Kriz + Hata</option>
              <option value="izleyici">İzleyici — Haftalık + Kriz</option>
              <option value="teknik">Teknik — Yalnızca Hata bildirimi</option>
            </select>
          </div>
          {hata && <p className="text-xs text-red-600">{hata}</p>}
          <div className="flex justify-end gap-2">
            <button onClick={() => { setFormAcik(false); setHata(""); }} className="btn-ghost text-sm">İptal</button>
            <button
              onClick={() => ekle.mutate(form)}
              disabled={ekle.isPending || !form.ad_soyad || !form.email}
              className="btn-primary text-sm disabled:opacity-50"
            >
              Ekle
            </button>
          </div>
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              {["Ad Soyad", "E-posta", "Rol", "Kayıt", "Durum", ""].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? [...Array(4)].map((_, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    {[...Array(6)].map((_, j) => (
                      <td key={j} className="px-4 py-3"><div className="h-4 bg-slate-100 rounded animate-pulse" /></td>
                    ))}
                  </tr>
                ))
              : alicilar.map(a => (
                  <tr key={a.id} className={cn("border-b border-slate-50 table-row-hover", !a.aktif && "opacity-50")}>
                    <td className="px-4 py-3 font-medium text-slate-900">{a.ad_soyad}</td>
                    <td className="px-4 py-3 text-slate-500 font-mono text-xs">{a.email}</td>
                    <td className="px-4 py-3">
                      <span className={`badge ${ROL_BADGE[a.rol as Rol] ?? "bg-slate-100 text-slate-600"}`}>{a.rol}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{formatTarih(a.eklendi_at)}</td>
                    <td className="px-4 py-3">
                      <span className={`badge ${a.aktif ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                        {a.aktif ? "Aktif" : "Pasif"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => toggle.mutate({ email: a.email, aktif: !a.aktif })}
                          className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
                        >
                          {a.aktif ? <PowerOff size={15} /> : <Power size={15} />}
                        </button>
                        <button
                          onClick={() => { if (confirm(`${a.email} silinsin mi?`)) sil.mutate(a.email); }}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
            }
            {!isLoading && alicilar.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-400 text-sm">
                  Henüz alıcı eklenmemiş.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Rakip Firmalar Tab ────────────────────────────────────────────────────────
// NOT: Bu sekim tenant'a özel /tenant-competitors/ uçlarını kullanır — her yeni
// kurum boş bir listeyle başlar; rakipler yalnızca "Otomatik Bul" (LLM, tenant
// domaininden) veya manuel ekleme ile oluşur. Eski /competitors/ ucu (rakipFirmaApi)
// tenant'a göre filtrelenmez, kasıtlı olarak burada kullanılmaz.

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

function RakipSatiri({ rakip, onToggle, onSil }: { rakip: TenantRakip; onToggle: () => void; onSil: () => void }) {
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

function RakipFirmalar() {
  const qc = useQueryClient();
  const [yeniAcik, setYeniAcik] = useState(false);
  const [yeniForm, setYeniForm] = useState<RakipForm>(BOSH_FORM);
  const [silinecek, setSilinecek] = useState<number | null>(null);
  const [analizHata, setAnalizHata] = useState("");
  const [analizBekliyor, setAnalizBekliyor] = useState(false);

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

  const set = (k: keyof RakipForm) => (v: string) => setYeniForm(p => ({ ...p, [k]: v }));
  const aktifler = rakipler.filter(r => r.aktif);
  const pasifler = rakipler.filter(r => !r.aktif);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Rakip Firmalar</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {aktifler.length} aktif · {pasifler.length} pasif
          </p>
        </div>
        <div className="flex items-center gap-2">
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
      </div>

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
    </div>
  );
}

// ── LinkedIn Takip Tab ────────────────────────────────────────────────────────

interface LinkedInTag {
  id: number;
  tenant_id: number;
  tag: string;
  aciklama: string;
  kaynak: "ai" | "manuel";
  secili: boolean;
  olusturuldu_at: string;
}

const linkedinApi = {
  listele:  () => http.get<LinkedInTag[]>("/linkedin/tags").then(r => r.data),
  uret:     () => http.post<LinkedInTag[]>("/linkedin/tags/generate").then(r => r.data),
  ekle:     (tag: string, aciklama: string) =>
    http.post<LinkedInTag>("/linkedin/tags", { tag, aciklama }).then(r => r.data),
  toggle:   (id: number, secili: boolean) =>
    http.patch<LinkedInTag>(`/linkedin/tags/${id}`, { secili }).then(r => r.data),
  sil:      (id: number) => http.delete(`/linkedin/tags/${id}`),
  topluSec: (secili_idler: number[]) =>
    http.post<LinkedInTag[]>("/linkedin/tags/batch-select", { secili_idler }).then(r => r.data),
};

function LinkedInTakip() {
  const qc = useQueryClient();
  const [manuelForm, setManuelForm] = useState({ tag: "", aciklama: "" });
  const [manuelAcik, setManuelAcik] = useState(false);
  const [uretHata, setUretHata] = useState("");

  const { data: tagler = [], isLoading } = useQuery<LinkedInTag[]>({
    queryKey: ["linkedin-tags"],
    queryFn: linkedinApi.listele,
  });

  const uret = useMutation({
    mutationFn: linkedinApi.uret,
    onSuccess: (data) => { qc.setQueryData(["linkedin-tags"], data); setUretHata(""); },
    onError: (e: any) => setUretHata(e.response?.data?.detail ?? "LLM üretimi başarısız"),
  });

  const ekle = useMutation({
    mutationFn: () => linkedinApi.ekle(manuelForm.tag, manuelForm.aciklama),
    onSuccess: (yeni) => {
      qc.setQueryData<LinkedInTag[]>(["linkedin-tags"], old => [...(old ?? []), yeni]);
      setManuelForm({ tag: "", aciklama: "" });
      setManuelAcik(false);
    },
  });

  const toggle = useMutation({
    mutationFn: ({ id, secili }: { id: number; secili: boolean }) =>
      linkedinApi.toggle(id, secili),
    onSuccess: (guncellendi) => {
      qc.setQueryData<LinkedInTag[]>(["linkedin-tags"],
        old => (old ?? []).map(t => t.id === guncellendi.id ? guncellendi : t)
      );
    },
  });

  const sil = useMutation({
    mutationFn: (id: number) => linkedinApi.sil(id),
    onSuccess: (_, id) => {
      qc.setQueryData<LinkedInTag[]>(["linkedin-tags"],
        old => (old ?? []).filter(t => t.id !== id)
      );
    },
  });

  const topluToggle = (seciliMi: boolean) => {
    const idler = seciliMi ? tagler.map(t => t.id) : [];
    linkedinApi.topluSec(idler).then(data => qc.setQueryData(["linkedin-tags"], data));
  };

  const aiTagler = tagler.filter(t => t.kaynak === "ai");
  const manuelTagler = tagler.filter(t => t.kaynak === "manuel");
  const seciliSayi = tagler.filter(t => t.secili).length;

  const TagSatiri = ({ t }: { t: LinkedInTag }) => (
    <div className={cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors group",
      t.secili ? "border-brand-200 bg-brand-50" : "border-slate-200 bg-white opacity-60"
    )}>
      <input
        type="checkbox"
        className="w-4 h-4 rounded accent-brand-600 shrink-0 cursor-pointer"
        checked={t.secili}
        onChange={() => toggle.mutate({ id: t.id, secili: !t.secili })}
      />
      <div className="flex-1 min-w-0">
        <span className={cn("text-sm font-semibold", t.secili ? "text-brand-700" : "text-slate-500")}>
          {t.tag}
        </span>
        {t.aciklama && (
          <p className="text-xs text-slate-400 truncate">{t.aciklama}</p>
        )}
      </div>
      <button
        onClick={() => sil.mutate(t.id)}
        className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all"
      >
        <Trash2 size={13} />
      </button>
    </div>
  );

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">LinkedIn Tag Takibi</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {seciliSayi} seçili · {tagler.length} toplam
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => uret.mutate()}
            disabled={uret.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-brand-300 text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors disabled:opacity-50"
          >
            <Sparkles size={15} className={uret.isPending ? "animate-pulse" : ""} />
            {uret.isPending ? "Üretiliyor…" : "Otomatik Üret"}
          </button>
          <button
            onClick={() => setManuelAcik(v => !v)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> Manuel Ekle
          </button>
        </div>
      </div>

      {/* LLM hata */}
      {uretHata && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex items-center justify-between">
          <span>{uretHata}</span>
          <button onClick={() => setUretHata("")} className="ml-3 text-red-400 hover:text-red-600">
            <X size={14} />
          </button>
        </div>
      )}

      {/* LLM üretim banner */}
      {uret.isPending && (
        <div className="rounded-lg bg-brand-50 border border-brand-200 px-4 py-3 text-sm text-brand-700 flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin shrink-0" />
          E-posta uzantınızdan sektör tespit ediliyor, LinkedIn keyword'leri oluşturuluyor…
        </div>
      )}

      {/* Manuel ekleme formu */}
      {manuelAcik && (
        <div className="card p-4 border-brand-200 bg-brand-50 space-y-3">
          <h3 className="text-sm font-semibold text-brand-900">Manuel Tag Ekle</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label mb-1">Hashtag / Keyword <span className="text-red-500">*</span></label>
              <input
                className="input font-mono text-sm"
                placeholder="#UlakHaberlesme veya Ulak Haberleşme"
                value={manuelForm.tag}
                onChange={e => setManuelForm(f => ({ ...f, tag: e.target.value }))}
              />
              <p className="text-xs text-slate-400 mt-0.5">
                # eklenmemişse otomatik eklenir
              </p>
            </div>
            <div>
              <label className="label mb-1">Açıklama (opsiyonel)</label>
              <input
                className="input text-sm"
                placeholder="Neden takip ediyorsunuz?"
                value={manuelForm.aciklama}
                onChange={e => setManuelForm(f => ({ ...f, aciklama: e.target.value }))}
              />
            </div>
          </div>
          {ekle.isError && (
            <p className="text-xs text-red-600">
              {(ekle.error as any)?.response?.data?.detail ?? "Bir hata oluştu"}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button onClick={() => setManuelAcik(false)} className="btn-ghost text-sm">İptal</button>
            <button
              onClick={() => ekle.mutate()}
              disabled={ekle.isPending || !manuelForm.tag.trim()}
              className="btn-primary text-sm disabled:opacity-50 flex items-center gap-1.5"
            >
              <Plus size={14} /> Ekle
            </button>
          </div>
        </div>
      )}

      {/* Toplu işlem çubuğu */}
      {tagler.length > 0 && (
        <div className="flex items-center justify-between px-1">
          <div className="flex gap-4 text-xs text-slate-500">
            <span><strong className="text-slate-700">{aiTagler.length}</strong> AI üretimi</span>
            <span><strong className="text-slate-700">{manuelTagler.length}</strong> manuel</span>
          </div>
          <div className="flex gap-3">
            <button className="text-xs text-brand-600 hover:underline font-medium"
              onClick={() => topluToggle(true)}>
              Tümünü Seç
            </button>
            <span className="text-slate-300">·</span>
            <button className="text-xs text-slate-500 hover:underline"
              onClick={() => topluToggle(false)}>
              Seçimi Temizle
            </button>
          </div>
        </div>
      )}

      {/* Tag listeleri */}
      {isLoading ? (
        <div className="text-center py-8 text-slate-400 text-sm">Yükleniyor…</div>
      ) : tagler.length === 0 ? (
        <div className="text-center py-12 text-slate-400 text-sm space-y-2">
          <Network size={32} className="mx-auto opacity-30" />
          <p>Henüz tag eklenmemiş.</p>
          <p className="text-xs">
            "LLM ile Üret" ile otomatik oluşturun veya "Manuel Ekle" ile kendiniz ekleyin.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {aiTagler.length > 0 && (
            <section className="space-y-2">
              <h3 className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                <Sparkles size={12} className="text-brand-500" />
                AI Önerileri — {aiTagler.length} tag
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {aiTagler.map(t => <TagSatiri key={t.id} t={t} />)}
              </div>
            </section>
          )}
          {manuelTagler.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-1">
                Manuel Eklenenler — {manuelTagler.length} tag
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {manuelTagler.map(t => <TagSatiri key={t.id} t={t} />)}
              </div>
            </section>
          )}
        </div>
      )}

      <div className="card p-4 bg-blue-50 border-blue-200">
        <p className="text-xs text-blue-700 leading-relaxed">
          <strong>Nasıl çalışır?</strong> Seçili her tag için DuckDuckGo üzerinden
          <code className="mx-1 bg-blue-100 px-1 rounded">site:linkedin.com/posts &lt;tag&gt;</code>
          araması yapılır. Bulunan gönderiler AI ile analiz edilerek PDF rapora eklenir.
        </p>
      </div>
    </div>
  );
}

// ── Ana Sayfa ─────────────────────────────────────────────────────────────────

const TABS: { key: Tab; label: string }[] = [
  { key: "llm",      label: "LLM Konfigürasyonu" },
  { key: "rakip",    label: "Rakip Firmalar"      },
  { key: "mail",     label: "Mail Listesi"        },
  { key: "linkedin", label: "LinkedIn Takip"      },
];

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const paramTab = searchParams.get("tab") as Tab | null;
  const [tab, setTab] = useState<Tab>(
    TABS.some(t => t.key === paramTab) ? paramTab! : "llm"
  );

  useEffect(() => {
    const p = searchParams.get("tab") as Tab | null;
    if (p && TABS.some(t => t.key === p) && p !== tab) setTab(p);
  }, [searchParams]);

  const handleTab = (k: Tab) => {
    setTab(k);
    setSearchParams({ tab: k }, { replace: true });
  };

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Settings2 size={22} className="text-brand-600" />
          <h1 className="text-2xl font-semibold text-slate-900">Ayarlar</h1>
        </div>
        <p className="text-slate-500 text-sm">
          {TABS.find(t => t.key === tab)?.label}
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 bg-slate-100 rounded-xl w-fit">
        {TABS.map(({ key: k, label: l }) => (
          <button
            key={k}
            onClick={() => handleTab(k)}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all",
              tab === k ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            )}
          >
            {l}
          </button>
        ))}
      </div>

      {tab === "llm"      && <LLMKonfigurasyonu />}
      {tab === "rakip"    && <RakipFirmalar />}
      {tab === "mail"     && <MailListesi />}
      {tab === "linkedin" && <LinkedInTakip />}
    </div>
  );
}
