import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus, FileText, Loader2, CheckCircle2, XCircle,
  Clock, Download, X, ChevronDown, ChevronUp, Trash2, Eye, UserPlus, Building2, Sparkles, Eraser, Send,
} from "lucide-react";
import {
  reportJobApi, raporApi, rakipFirmaApi, mailApi,
  type RaporJob, type Rapor, type RakipFirma, type Alici, type AliciOlustur, type RakipFirmaOlustur,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatTarihSaat, formatTarih } from "@/lib/utils";

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ durum }: { durum: RaporJob["durum"] }) {
  const map = {
    kuyrukta:   { cls: "bg-slate-100 text-slate-600",   icon: Clock,         label: "Kuyrukta"     },
    calisiyor:  { cls: "bg-blue-100 text-blue-700",      icon: Loader2,       label: "Hazırlanıyor" },
    tamamlandi: { cls: "bg-green-100 text-green-700",    icon: CheckCircle2,  label: "Tamamlandı"   },
    hata:       { cls: "bg-red-100 text-red-700",        icon: XCircle,       label: "Hata"         },
  };
  const { cls, icon: Icon, label } = map[durum] ?? map.kuyrukta;
  return (
    <span className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium w-fit", cls)}>
      <Icon size={12} className={durum === "calisiyor" ? "animate-spin" : ""} />
      {label}
    </span>
  );
}

// ── Rapor oluşturma modali ────────────────────────────────────────────────────

function RaporOlusturModal({ onKapat }: { onKapat: () => void }) {
  const qc = useQueryClient();
  const [gun, setGun] = useState(7);
  const [kapsam, setKapsam] = useState<"sadece_ben" | "secili" | "hepsi">("hepsi");
  const [seciliRakipler, setSeciliRakipler] = useState<Set<number>>(new Set());
  const [seciliMail, setSeciliMail] = useState<Set<string>>(new Set());
  const [hata, setHata] = useState("");
  const [yeniAliciFormu, setYeniAliciFormu] = useState(false);
  const [yeniAdSoyad, setYeniAdSoyad] = useState("");
  const [yeniEmail, setYeniEmail] = useState("");
  const [aliciHata, setAliciHata] = useState("");

  const [yeniRakipFormu, setYeniRakipFormu] = useState(false);
  const [yeniRakipAd, setYeniRakipAd] = useState("");
  const [yeniRakipBolge, setYeniRakipBolge] = useState("");
  const [yeniRakipSorgu, setYeniRakipSorgu] = useState("");
  const [yeniRakipDil, setYeniRakipDil] = useState<"tr" | "en">("en");
  const [rakipHata, setRakipHata] = useState("");
  const [analizBilgi, setAnalizBilgi] = useState("");

  const { data: rakipler = [] } = useQuery<RakipFirma[]>({
    queryKey: ["rakipler"],
    queryFn: rakipFirmaApi.listele,
  });

  const { data: alicilar = [] } = useQuery<Alici[]>({
    queryKey: ["mail"],
    queryFn: mailApi.listele,
  });

  // Tüm aktif alıcıları başlangıçta seç
  useEffect(() => {
    if (alicilar.length && seciliMail.size === 0) {
      setSeciliMail(new Set(alicilar.filter(a => a.aktif).map(a => a.email)));
    }
  }, [alicilar]);

  const olustur = useMutation({
    mutationFn: () => reportJobApi.olustur({
      gun,
      kapsam,
      rakipler: kapsam === "secili"
        ? rakipler.filter(r => seciliRakipler.has(r.id)).map(r => r.ad)
        : [],
      mail_alicilari: [...seciliMail],
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["report-jobs"] });
      onKapat();
    },
    onError: (e: any) => setHata(e.response?.data?.detail ?? "Bir hata oluştu"),
  });

  const toggleRakip = (id: number) =>
    setSeciliRakipler(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });

  const toggleMail = (email: string) =>
    setSeciliMail(prev => { const s = new Set(prev); s.has(email) ? s.delete(email) : s.add(email); return s; });

  const aliciEkle = useMutation({
    mutationFn: (data: AliciOlustur) => mailApi.ekle(data),
    onSuccess: (yeni) => {
      qc.invalidateQueries({ queryKey: ["mail"] });
      setSeciliMail(prev => new Set([...prev, yeni.email]));
      setYeniAdSoyad("");
      setYeniEmail("");
      setAliciHata("");
      setYeniAliciFormu(false);
    },
    onError: (e: any) => setAliciHata(e.response?.data?.detail ?? "Alıcı eklenemedi"),
  });

  const aliciEkleSubmit = () => {
    setAliciHata("");
    if (!yeniAdSoyad.trim()) { setAliciHata("Ad Soyad zorunlu"); return; }
    if (!yeniEmail.trim() || !yeniEmail.includes("@")) { setAliciHata("Geçerli bir e-posta girin"); return; }
    aliciEkle.mutate({ ad_soyad: yeniAdSoyad.trim(), email: yeniEmail.trim().toLowerCase(), rol: "izleyici", haftalik: true, kriz: false, hata: false });
  };

  const rakipEkle = useMutation({
    mutationFn: (d: RakipFirmaOlustur) => rakipFirmaApi.ekle(d),
    onSuccess: (yeni) => {
      qc.invalidateQueries({ queryKey: ["rakipler"] });
      setSeciliRakipler(prev => new Set([...prev, yeni.id]));
      setYeniRakipAd(""); setYeniRakipBolge(""); setYeniRakipSorgu("");
      setRakipHata(""); setYeniRakipFormu(false);
    },
    onError: (e: any) => setRakipHata(e.response?.data?.detail ?? "Rakip eklenemedi"),
  });

  const rakipSil = useMutation({
    mutationFn: (id: number) => rakipFirmaApi.sil(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["rakipler"] });
      setSeciliRakipler(prev => { const s = new Set(prev); s.delete(id); return s; });
    },
  });

  const rakipAnaliz = useMutation({
    mutationFn: () => rakipFirmaApi.analiz(),
    onSuccess: (bulunan) => {
      qc.invalidateQueries({ queryKey: ["rakipler"] });
      // Yeni eklenen rakipleri otomatik seç
      setSeciliRakipler(prev => new Set([...prev, ...bulunan.map(r => r.id)]));
      const yeni = bulunan.length;
      setAnalizBilgi(yeni > 0 ? `${yeni} yeni rakip eklendi ve seçildi.` : "Yeni rakip bulunamadı (tümü zaten mevcut).");
      setRakipHata("");
    },
    onError: (e: any) => {
      setRakipHata(e.response?.data?.detail ?? "LLM analizi başarısız oldu.");
      setAnalizBilgi("");
    },
  });

  const rakipEkleSubmit = () => {
    setRakipHata("");
    if (!yeniRakipAd.trim()) { setRakipHata("Ad zorunlu"); return; }
    if (!yeniRakipBolge.trim()) { setRakipHata("Bölge zorunlu"); return; }
    if (!yeniRakipSorgu.trim()) { setRakipHata("RSS sorgusu zorunlu"); return; }
    rakipEkle.mutate({
      ad: yeniRakipAd.trim(),
      bolge: yeniRakipBolge.trim(),
      rss_sorgu: yeniRakipSorgu.trim(),
      rss_dil: yeniRakipDil,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 sticky top-0 bg-white">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Yeni Rapor Oluştur</h2>
            <p className="text-slate-500 text-sm mt-0.5">Parametreleri belirleyin ve raporu kuyruğa alın</p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* Zaman aralığı */}
          <div>
            <label className="label mb-3">Zaman Aralığı</label>
            <div className="flex gap-2">
              {([3, 7, 15, 30] as const).map(d => (
                <button
                  key={d}
                  onClick={() => setGun(d)}
                  className={cn(
                    "flex-1 py-2.5 rounded-lg text-sm font-medium border transition-colors",
                    gun === d
                      ? "bg-brand-600 text-white border-brand-600"
                      : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                  )}
                >
                  {d} gün
                </button>
              ))}
            </div>
          </div>

          {/* Kapsam */}
          <div>
            <label className="label mb-3">Analiz Edilecek Şirketler</label>
            <div className="space-y-2">
              {[
                { value: "sadece_ben", label: "Sadece kendi şirketim",  desc: "Yalnızca kurumunuza ait haberler analiz edilir" },
                { value: "secili",     label: "Seçili rakipler",         desc: "Aşağıdan seçeceğiniz rakipler dahil edilir" },
                { value: "hepsi",      label: "Tümü",                   desc: "Kendi şirketiniz + tüm aktif rakipler" },
              ].map(opt => (
                <label
                  key={opt.value}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-colors",
                    kapsam === opt.value ? "border-brand-300 bg-brand-50" : "border-slate-200 hover:bg-slate-50"
                  )}
                >
                  <input
                    type="radio"
                    name="kapsam"
                    value={opt.value}
                    checked={kapsam === opt.value}
                    onChange={() => setKapsam(opt.value as typeof kapsam)}
                    className="mt-0.5 accent-brand-600"
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-800">{opt.label}</p>
                    <p className="text-xs text-slate-500">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Rakip seçimi (kapsam=secili ise) */}
          {kapsam === "secili" && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="label">
                  Rakip Seçimi
                  {seciliRakipler.size > 0 && (
                    <span className="text-xs text-slate-400 ml-2 font-normal">
                      {seciliRakipler.size} seçili
                    </span>
                  )}
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setAnalizBilgi("");
                      setRakipHata("");
                      rakipAnaliz.mutate();
                    }}
                    disabled={rakipAnaliz.isPending}
                    className="flex items-center gap-1 text-xs text-violet-600 hover:text-violet-700 font-medium disabled:opacity-50"
                    title="Şirketinizin domain'ine göre Claude AI ile rakip firmaları otomatik bul"
                  >
                    {rakipAnaliz.isPending
                      ? <Loader2 size={13} className="animate-spin" />
                      : <Sparkles size={13} />}
                    {rakipAnaliz.isPending ? "Analiz ediliyor…" : "LLM ile Otomatik Bul"}
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    type="button"
                    onClick={() => { setYeniRakipFormu(v => !v); setRakipHata(""); setAnalizBilgi(""); }}
                    className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium"
                  >
                    <Building2 size={13} />
                    {yeniRakipFormu ? "İptal" : "Manuel Ekle"}
                  </button>
                </div>
              </div>

              {/* Analiz geri bildirim mesajları */}
              {analizBilgi && (
                <div className="mb-2 flex items-center gap-2 text-xs text-violet-700 bg-violet-50 border border-violet-200 rounded-lg px-3 py-2">
                  <Sparkles size={12} />
                  {analizBilgi}
                </div>
              )}
              {rakipHata && !yeniRakipFormu && (
                <p className="mb-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {rakipHata}
                </p>
              )}

              {/* Yeni rakip formu */}
              {yeniRakipFormu && (
                <div className="mb-3 p-3 border border-brand-200 bg-brand-50 rounded-xl space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Ad (örn: OneWeb)"
                      value={yeniRakipAd}
                      onChange={e => setYeniRakipAd(e.target.value)}
                      className="input text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Bölge (örn: İngiltere)"
                      value={yeniRakipBolge}
                      onChange={e => setYeniRakipBolge(e.target.value)}
                      className="input text-sm"
                    />
                  </div>
                  <input
                    type="text"
                    placeholder="RSS Sorgusu (örn: OneWeb satellite news)"
                    value={yeniRakipSorgu}
                    onChange={e => setYeniRakipSorgu(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && rakipEkleSubmit()}
                    className="input text-sm font-mono"
                  />
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex gap-1">
                      {(["tr", "en"] as const).map(d => (
                        <button
                          key={d}
                          type="button"
                          onClick={() => setYeniRakipDil(d)}
                          className={cn(
                            "px-3 py-1 rounded-lg text-xs font-medium border transition-colors",
                            yeniRakipDil === d
                              ? "bg-brand-600 text-white border-brand-600"
                              : "bg-white text-slate-600 border-slate-200",
                          )}
                        >
                          {d.toUpperCase()}
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={rakipEkleSubmit}
                      disabled={rakipEkle.isPending}
                      className="btn-primary text-xs py-1.5 px-3 disabled:opacity-50"
                    >
                      {rakipEkle.isPending ? <Loader2 size={12} className="animate-spin" /> : "Ekle ve Seç"}
                    </button>
                  </div>
                  {rakipHata && <p className="text-xs text-red-600">{rakipHata}</p>}
                </div>
              )}

              {rakipler.length === 0 && !yeniRakipFormu ? (
                <p className="text-sm text-slate-400">
                  Henüz rakip eklenmemiş. Yukarıdan ekleyebilirsiniz.
                </p>
              ) : rakipler.length > 0 && (
                <div className="grid grid-cols-2 gap-1 max-h-64 overflow-y-auto pr-1">
                  {[...rakipler].sort((a, b) => a.id - b.id).map(r => (
                    <div key={r.id} className="flex items-center gap-2 p-2 rounded-lg hover:bg-slate-50 group">
                      <label className="flex items-start gap-2 cursor-pointer flex-1 min-w-0">
                        <input
                          type="checkbox"
                          className="mt-0.5 w-4 h-4 rounded accent-brand-600 shrink-0"
                          checked={seciliRakipler.has(r.id)}
                          onChange={() => toggleRakip(r.id)}
                        />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-800 truncate">{r.ad}</p>
                          <p className="text-xs text-slate-400 truncate">{r.bolge} · {r.rss_dil.toUpperCase()}</p>
                        </div>
                      </label>
                      <button
                        type="button"
                        onClick={() => rakipSil.mutate(r.id)}
                        disabled={rakipSil.isPending}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition-all shrink-0"
                        title="Rakibi sil"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mail alıcıları */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label">Rapor Gönderilecek Alıcılar</label>
              <button
                type="button"
                onClick={() => { setYeniAliciFormu(v => !v); setAliciHata(""); }}
                className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium"
              >
                <UserPlus size={13} />
                {yeniAliciFormu ? "İptal" : "Yeni Alıcı Ekle"}
              </button>
            </div>

            {/* Yeni alıcı formu */}
            {yeniAliciFormu && (
              <div className="mb-3 p-3 border border-brand-200 bg-brand-50 rounded-xl space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Ad Soyad"
                    value={yeniAdSoyad}
                    onChange={e => setYeniAdSoyad(e.target.value)}
                    className="input text-sm"
                  />
                  <input
                    type="email"
                    placeholder="E-posta"
                    value={yeniEmail}
                    onChange={e => setYeniEmail(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && aliciEkleSubmit()}
                    className="input text-sm"
                  />
                </div>
                {aliciHata && <p className="text-xs text-red-600">{aliciHata}</p>}
                <button
                  type="button"
                  onClick={aliciEkleSubmit}
                  disabled={aliciEkle.isPending}
                  className="btn-primary text-xs py-1.5 px-3 disabled:opacity-50"
                >
                  {aliciEkle.isPending ? <Loader2 size={12} className="animate-spin" /> : "Ekle ve Seç"}
                </button>
              </div>
            )}

            {alicilar.filter(a => a.aktif).length === 0 && !yeniAliciFormu ? (
              <p className="text-sm text-slate-400">
                Mail listesinde aktif alıcı yok. Yukarıdan yeni alıcı ekleyebilirsiniz.
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {alicilar.filter(a => a.aktif).map(a => (
                  <label key={a.email} className="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-slate-50">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded accent-brand-600"
                      checked={seciliMail.has(a.email)}
                      onChange={() => toggleMail(a.email)}
                    />
                    <div>
                      <p className="text-sm font-medium text-slate-800">{a.ad_soyad}</p>
                      <p className="text-xs text-slate-400 font-mono">{a.email}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          {hata && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
              {hata}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-100 sticky bottom-0 bg-white">
          <button onClick={onKapat} className="btn-ghost">İptal</button>
          <button
            onClick={() => olustur.mutate()}
            disabled={olustur.isPending}
            className="btn-primary disabled:opacity-50"
          >
            {olustur.isPending ? <><Loader2 size={16} className="animate-spin" /> Kuyruğa alınıyor…</> : "Raporu Başlat"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Job satırı ────────────────────────────────────────────────────────────────

function JobSatiri({ job, onSil }: { job: RaporJob; onSil: () => void }) {
  const [acik, setAcik] = useState(false);
  const [gonderAcik, setGonderAcik] = useState(false);
  const rakipler: string[] = JSON.parse(job.rakipler_json || "[]");
  const silinebilir = job.durum !== "calisiyor";

  return (
    <div className={cn("border rounded-xl overflow-hidden transition-colors",
      job.durum === "hata" ? "border-red-200" : "border-slate-200")}>
      <div className="flex items-center gap-4 px-4 py-3">
        <StatusBadge durum={job.durum} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-800">Son {job.gun} Gün</span>
            <span className="badge bg-slate-100 text-slate-600 capitalize">{job.kapsam.replace("_", " ")}</span>
            {rakipler.length > 0 && (
              <span className="text-xs text-slate-400">{rakipler.length} rakip</span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{formatTarihSaat(job.olusturuldu_at)}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {job.durum === "tamamlandi" && job.dosya_yolu && (
            <button
              onClick={() => reportJobApi.indir(job.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <Download size={13} /> İndir
            </button>
          )}
          {job.durum === "tamamlandi" && job.rapor_id && (
            <button
              onClick={() => setGonderAcik(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <Send size={13} /> Gönder
            </button>
          )}
          {(job.hata_mesaji || rakipler.length > 0) && (
            <button
              onClick={() => setAcik(a => !a)}
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors"
            >
              {acik ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
          )}
          {silinebilir && (
            <button
              onClick={onSil}
              className="p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Kaydı sil"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {acik && (
        <div className="border-t border-slate-100 px-4 py-3 bg-slate-50 space-y-2">
          {job.hata_mesaji && (
            <pre className="text-xs text-red-700 bg-red-50 rounded-lg p-3 overflow-auto max-h-32 whitespace-pre-wrap">
              {job.hata_mesaji}
            </pre>
          )}
          {rakipler.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {rakipler.map(r => (
                <span key={r} className="badge bg-white border border-slate-200 text-slate-600">{r}</span>
              ))}
            </div>
          )}
        </div>
      )}
      {gonderAcik && job.rapor_id && (
        <RaporGonderModal
          raporId={job.rapor_id}
          baslik={`Son ${job.gun} Gün — ${formatTarihSaat(job.olusturuldu_at)}`}
          onKapat={() => setGonderAcik(false)}
        />
      )}
    </div>
  );
}

// ── Rapor gönderme modali ─────────────────────────────────────────────────────

function RaporGonderModal({ raporId, baslik, onKapat }: { raporId: number; baslik: string; onKapat: () => void }) {
  const [emailInput, setEmailInput] = useState("");
  const [mesaj, setMesaj] = useState("");
  const [hata, setHata] = useState("");
  const [basarili, setBasarili] = useState(false);

  const gonderMutation = useMutation({
    mutationFn: (data: { emails: string[]; mesaj: string }) => raporApi.gonder(raporId, data),
    onSuccess: () => {
      setBasarili(true);
      setTimeout(onKapat, 1500);
    },
    onError: (e: any) => setHata(e.response?.data?.detail ?? "E-posta gönderilemedi"),
  });

  const gonderSubmit = () => {
    setHata("");
    const emails = emailInput.split(/[,\n]/).map(e => e.trim()).filter(Boolean);
    if (emails.length === 0) { setHata("En az bir e-posta adresi girin"); return; }
    gonderMutation.mutate({ emails, mesaj: mesaj.trim() });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Raporu Gönder</h2>
            <p className="text-slate-500 text-sm mt-0.5 truncate max-w-[280px]">"{baslik}"</p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors shrink-0">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        {basarili ? (
          <div className="px-6 py-8 flex flex-col items-center text-center gap-2">
            <CheckCircle2 size={32} className="text-green-600" />
            <p className="text-sm font-medium text-slate-800">Gönderildi</p>
          </div>
        ) : (
          <div className="px-6 py-5 space-y-4">
            <div>
              <label className="label mb-1.5">Alıcı E-posta(lar)</label>
              <textarea
                autoFocus
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                placeholder="ornek@sirket.com, diger@sirket.com"
                rows={2}
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-brand-300 resize-none"
              />
              <p className="text-xs text-slate-400 mt-1">Birden fazla adresi virgülle ayırın</p>
            </div>
            <div>
              <label className="label mb-1.5">Mesaj (isteğe bağlı)</label>
              <textarea
                value={mesaj}
                onChange={e => setMesaj(e.target.value)}
                placeholder="Kısa bir not ekleyin..."
                rows={3}
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-brand-300 resize-none"
              />
            </div>
            {hata && <p className="text-xs text-red-600">{hata}</p>}
            <button
              onClick={gonderSubmit}
              disabled={gonderMutation.isPending}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {gonderMutation.isPending
                ? <><Loader2 size={14} className="animate-spin" /> Gönderiliyor...</>
                : <><Send size={14} /> Gönder</>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Arşiv satırı ─────────────────────────────────────────────────────────────

function ArsivSatiri({ rapor, onSil }: { rapor: Rapor; onSil: () => void }) {
  const qc = useQueryClient();
  const [duzenle, setDuzenle] = useState(false);
  const [adInput, setAdInput] = useState(rapor.ad ?? "");
  const [gonderAcik, setGonderAcik] = useState(false);

  const adGuncellemeMutation = useMutation({
    mutationFn: (ad: string) => raporApi.adGuncelle(rapor.id, ad),
    onSuccess: (guncellendi) => {
      qc.setQueryData<Rapor[]>(["reports-arsiv"], old =>
        (old ?? []).map(r => r.id === guncellendi.id ? guncellendi : r)
      );
      setDuzenle(false);
    },
  });

  const tarihAraligi = rapor.baslangic_tarih && rapor.bitis_tarih
    ? `${formatTarih(rapor.baslangic_tarih)} – ${formatTarih(rapor.bitis_tarih)}`
    : null;

  const baslik = rapor.ad || tarihAraligi || formatTarihSaat(rapor.olusturuldu_at);

  return (
    <div className="flex items-start gap-4 px-4 py-3 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors group">
      <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 mt-0.5">
        <FileText size={15} className="text-slate-500" />
      </div>
      <div className="flex-1 min-w-0">
        {duzenle ? (
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => { e.preventDefault(); adGuncellemeMutation.mutate(adInput); }}
          >
            <input
              autoFocus
              value={adInput}
              onChange={e => setAdInput(e.target.value)}
              className="flex-1 text-sm border border-brand-400 rounded-lg px-2 py-1 outline-none focus:ring-2 focus:ring-brand-300"
              maxLength={120}
              placeholder="Rapor adı..."
            />
            <button
              type="submit"
              disabled={adGuncellemeMutation.isPending || !adInput.trim()}
              className="px-2.5 py-1 text-xs bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50"
            >
              {adGuncellemeMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : "Kaydet"}
            </button>
            <button type="button" onClick={() => { setAdInput(rapor.ad ?? ""); setDuzenle(false); }} className="px-2 py-1 text-xs text-slate-500 hover:text-slate-700">İptal</button>
          </form>
        ) : (
          <div className="flex items-center gap-1.5">
            <p className="text-sm font-medium text-slate-800 truncate">{baslik}</p>
            <button
              onClick={() => { setAdInput(rapor.ad ?? ""); setDuzenle(true); }}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-400 hover:text-brand-600 transition-all"
              title="Adı düzenle"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
          </div>
        )}
        <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1.5 flex-wrap">
          {tarihAraligi && rapor.ad && (
            <span className="text-slate-300">({tarihAraligi})</span>
          )}
          {rapor.haber_sayisi != null && <span>{rapor.haber_sayisi} haber</span>}
          {(tarihAraligi || rapor.haber_sayisi != null) && <span>·</span>}
          <span>Oluşturuldu: {formatTarihSaat(rapor.olusturuldu_at)}</span>
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {rapor.dosya_var ? (
          <>
            <button
              onClick={() => raporApi.goruntule(rapor.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-600 hover:bg-white transition-colors"
            >
              <Eye size={13} /> Görüntüle
            </button>
            <button
              onClick={() => raporApi.indir(rapor.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-600 hover:bg-white transition-colors"
            >
              <Download size={13} /> İndir
            </button>
            <button
              onClick={() => setGonderAcik(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-600 hover:bg-white transition-colors"
            >
              <Send size={13} /> Gönder
            </button>
          </>
        ) : (
          <span className="text-xs text-slate-300">PDF yok</span>
        )}
        <button
          onClick={onSil}
          className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
          title="Raporu sil"
        >
          <Trash2 size={15} />
        </button>
      </div>
      {gonderAcik && (
        <RaporGonderModal
          raporId={rapor.id}
          baslik={rapor.ad || formatTarihSaat(rapor.olusturuldu_at)}
          onKapat={() => setGonderAcik(false)}
        />
      )}
    </div>
  );
}

// ── Ana Sayfa ─────────────────────────────────────────────────────────────────

export default function Reports() {
  const qc = useQueryClient();
  const [modalAcik, setModalAcik] = useState(false);
  const [silinecek, setSilinecek] = useState<number | null>(null);

  const silMutation = useMutation({
    mutationFn: (id: number) => raporApi.sil(id),
    onSuccess: () => {
      qc.setQueryData<Rapor[]>(["reports-arsiv"], old => (old ?? []).filter(r => r.id !== silinecek));
      setSilinecek(null);
    },
  });

  const jobSilMutation = useMutation({
    mutationFn: (id: number) => reportJobApi.sil(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["report-jobs"] }),
  });

  const hatalariTemizleMutation = useMutation({
    mutationFn: () => reportJobApi.hatalariTemizle(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["report-jobs"] }),
  });

  const { data: jobs = [], isLoading: jobsYukleniyor } = useQuery<RaporJob[]>({
    queryKey: ["report-jobs"],
    queryFn: reportJobApi.listele,
    refetchInterval: (data) => {
      const aktif = (data?.state?.data as RaporJob[] ?? []).some(
        j => j.durum === "kuyrukta" || j.durum === "calisiyor"
      );
      return aktif ? 3000 : false;
    },
  });

  const hataliJobSayisi = jobs.filter(j => j.durum === "hata" || (j.durum === "kuyrukta" && new Date(j.olusturuldu_at + "Z").getTime() < Date.now() - 3_600_000)).length;

  const { data: arsiv = [], isLoading: arsivYukleniyor } = useQuery<Rapor[]>({
    queryKey: ["reports-arsiv"],
    queryFn: () => raporApi.listele(50),
  });

  const calisan = jobs.filter(j => j.durum === "kuyrukta" || j.durum === "calisiyor").length;

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileText size={22} className="text-brand-600" />
            <h1 className="text-2xl font-semibold text-slate-900">Raporlar</h1>
          </div>
          <p className="text-slate-500 text-sm">
            Rapor oluşturun, durumlarını takip edin ve PDF'leri indirin
            {calisan > 0 && (
              <span className="ml-2 inline-flex items-center gap-1 text-blue-600">
                <Loader2 size={13} className="animate-spin" />
                {calisan} rapor hazırlanıyor
              </span>
            )}
          </p>
        </div>
        <button onClick={() => setModalAcik(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Rapor Oluştur
        </button>
      </div>

      {/* Aktif job listesi */}
      {jobsYukleniyor ? (
        <div className="space-y-3">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="border border-slate-200 rounded-xl h-16 animate-pulse bg-slate-50" />
          ))}
        </div>
      ) : jobs.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              İşlem Geçmişi
            </h2>
            {hataliJobSayisi > 0 && (
              <button
                onClick={() => hatalariTemizleMutation.mutate()}
                disabled={hatalariTemizleMutation.isPending}
                className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 font-medium disabled:opacity-50"
              >
                {hatalariTemizleMutation.isPending
                  ? <Loader2 size={12} className="animate-spin" />
                  : <Eraser size={12} />}
                {hataliJobSayisi} hatayı temizle
              </button>
            )}
          </div>
          <div className="space-y-3">
            {jobs.map(j => (
              <JobSatiri key={j.id} job={j} onSil={() => jobSilMutation.mutate(j.id)} />
            ))}
          </div>
        </section>
      )}

      {/* Arşiv (eski pipeline raporları) */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          PDF Arşivi
          {arsiv.length > 0 && <span className="ml-2 font-normal text-slate-400 normal-case">{arsiv.length} rapor</span>}
        </h2>
        {arsivYukleniyor ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="border border-slate-200 rounded-xl h-14 animate-pulse bg-slate-50" />
            ))}
          </div>
        ) : arsiv.length === 0 ? (
          <div className="card p-12 text-center">
            <FileText size={36} className="text-slate-200 mx-auto mb-3" />
            <p className="text-slate-500 text-sm font-medium">Henüz rapor oluşturulmamış</p>
            <p className="text-slate-400 text-xs mt-1">Rapor Oluştur butonuna tıklayarak başlatın.</p>
            <button onClick={() => setModalAcik(true)} className="btn-primary mt-4 mx-auto">
              <Plus size={16} /> İlk Raporu Oluştur
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {arsiv.map(r => (
              <ArsivSatiri key={r.id} rapor={r} onSil={() => setSilinecek(r.id)} />
            ))}
          </div>
        )}
      </section>

      {modalAcik && <RaporOlusturModal onKapat={() => setModalAcik(false)} />}

      {silinecek !== null && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="card p-6 max-w-sm w-full space-y-4">
            <h3 className="text-base font-semibold text-slate-900">Raporu sil?</h3>
            <p className="text-sm text-slate-500">
              Kayıt veritabanından silinir. PDF dosyası diskte kalmaya devam eder.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setSilinecek(null)} className="btn-ghost text-sm">İptal</button>
              <button
                onClick={() => silMutation.mutate(silinecek)}
                disabled={silMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              >
                {silMutation.isPending ? "Siliniyor…" : "Evet, sil"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
