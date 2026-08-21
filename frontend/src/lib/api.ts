import axios from "axios";

export const http = axios.create({ baseURL: "/api" });

// Auth token interceptor
http.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 401 → login'e yönlendir
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Kullanici {
  id: number;
  email: string;
  ad_soyad: string;
  rol: string;
  tenant_id: number;
  tenant_adi?: string;
  tenant_domain?: string;
}

export interface Alici {
  id: number;
  ad_soyad: string;
  email: string;
  rol: "yonetici" | "izleyici" | "teknik";
  haftalik: boolean;
  kriz: boolean;
  hata: boolean;
  aktif: boolean;
  eklendi_at: string;
}

export interface AliciOlustur {
  ad_soyad: string;
  email: string;
  rol: "yonetici" | "izleyici" | "teknik";
  haftalik: boolean;
  kriz: boolean;
  hata: boolean;
}

export interface AliciGuncelle {
  aktif?: boolean;
  rol?: "yonetici" | "izleyici" | "teknik";
  haftalik?: boolean;
  kriz?: boolean;
  hata?: boolean;
}

export interface Rapor {
  id: number;
  ad: string | null;
  olusturuldu_at: string;
  baslangic_tarih: string | null;
  bitis_tarih: string | null;
  haber_sayisi: number | null;
  dosya_yolu: string | null;
  dosya_var: boolean;
}

export interface RaporJob {
  id: number;
  tenant_id: number;
  durum: "kuyrukta" | "calisiyor" | "tamamlandi" | "hata";
  gun: number;
  kapsam: string;
  rakipler_json: string;
  mail_alicilari_json: string;
  hata_mesaji: string | null;
  rapor_id: number | null;
  dosya_yolu: string | null;
  baslangic_at: string | null;
  bitis_at: string | null;
  olusturuldu_at: string;
}

export interface RaporJobOlustur {
  gun: number;
  kapsam: string;
  rakipler: string[];
  mail_alicilari: string[];
}

export interface Istatistik {
  toplam_haber: number;
  olumlu: number;
  olumsuz: number;
  notr: number;
  son_rapor_tarihi: string | null;
  toplam_rapor: number;
  aktif_alici: number;
}

export interface TimelineVeri {
  gun: string;
  toplam: number;
  olumsuz: number;
}

export interface Rakip {
  ad: string;
  bolge: string;
  aciklama: string;
  ticker: string | null;
  kategori: string;
}

export interface TenantRakip {
  id: number;
  tenant_id: number;
  ad: string;
  aciklama: string;
  bolge: string;
  sektor: string;
  aktif: boolean;
  ai_onerisi: boolean;
  olusturuldu_at: string;
}

export interface RakipFirma {
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

export interface RakipFirmaOlustur {
  ad: string;
  rss_sorgu: string;
  rss_dil: "tr" | "en";
  ticker?: string;
  bolge: string;
  aciklama?: string;
}

export interface LLMConfig {
  id: number;
  tenant_id: number;
  provider_name: string;
  model_name: string;
  base_url: string | null;
  aktif: boolean;
  olusturuldu_at: string;
}

export interface PipelineDurumu {
  calisiyor: boolean;
  baslangic_zamani: string | null;
  bitis_zamani: string | null;
  sonuc: "basarili" | "hata" | null;
  hata: string | null;
}

export interface ModelAyar {
  model: string;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  kayit: (data: { email: string; sifre: string; ad_soyad: string; kurum_adi?: string }) =>
    http.post("/auth/register", data).then(r => r.data),
  giris: (email: string, sifre: string) =>
    http.post("/auth/login", { email, sifre }).then(r => r.data),
  me: () => http.get("/auth/me").then(r => r.data),
};

// ── Mail ─────────────────────────────────────────────────────────────────────

export const mailApi = {
  listele: ()                                    => http.get<Alici[]>("/mail/").then(r => r.data),
  ekle:    (data: AliciOlustur)                  => http.post<Alici>("/mail/", data).then(r => r.data),
  guncelle:(email: string, d: AliciGuncelle)     => http.patch<Alici>(`/mail/${encodeURIComponent(email)}`, d).then(r => r.data),
  sil:     (email: string)                       => http.delete(`/mail/${encodeURIComponent(email)}`),
};

// ── Reports (arşiv) ───────────────────────────────────────────────────────────

async function _pdfBlob(url: string): Promise<string> {
  const res = await http.get(url, { responseType: "blob" });
  const blob = new Blob([res.data], { type: "application/pdf" });
  return URL.createObjectURL(blob);
}

export const raporApi = {
  listele: (limit = 20, offset = 0) =>
    http.get<Rapor[]>("/reports/", { params: { limit, offset } }).then(r => r.data),
  goruntule: async (id: number) => {
    const url = await _pdfBlob(`/reports/${id}/view`);
    window.open(url, "_blank");
  },
  indir: async (id: number) => {
    const url = await _pdfBlob(`/reports/${id}/download`);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rapor_${id}.pdf`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  },
  adGuncelle: (id: number, ad: string) =>
    http.patch<Rapor>(`/reports/${id}`, { ad }).then(r => r.data),
  sil: (id: number) =>
    http.delete(`/reports/${id}`),
};

// ── Report Jobs (asenkron) ────────────────────────────────────────────────────

export const reportJobApi = {
  listele:         ()                      => http.get<RaporJob[]>("/report-jobs/").then(r => r.data),
  olustur:         (data: RaporJobOlustur) => http.post<RaporJob>("/report-jobs/", data).then(r => r.data),
  durumAl:         (id: number)            => http.get<RaporJob>(`/report-jobs/${id}`).then(r => r.data),
  indir:           async (id: number) => {
    const url = await _pdfBlob(`/report-jobs/${id}/download`);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rapor_${id}.pdf`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  },
  sil:             (id: number)            => http.delete(`/report-jobs/${id}`),
  hatalariTemizle: ()                      => http.delete<{ silinen: number }>("/report-jobs/").then(r => r.data),
};

// ── Stats ─────────────────────────────────────────────────────────────────────

export const statsApi = {
  al:       ()              => http.get<Istatistik>("/stats").then(r => r.data),
  timeline: (gun: number)   => http.get<TimelineVeri[]>("/stats/timeline", { params: { gun } }).then(r => r.data),
};

// ── Settings ─────────────────────────────────────────────────────────────────

export const settingsApi = {
  modelAl:      ()                   => http.get<ModelAyar>("/settings/model").then(r => r.data),
  modelGuncelle:(model: string)      => http.patch<ModelAyar>("/settings/model", { model }).then(r => r.data),
};

// ── Pipeline ──────────────────────────────────────────────────────────────────

export const pipelineApi = {
  rakipler: ()                               => http.get<Rakip[]>("/pipeline/competitors").then(r => r.data),
  durum:    ()                               => http.get<PipelineDurumu>("/pipeline/status").then(r => r.data),
  baslat:   (gun: number, rakipler: string[]) =>
    http.post("/pipeline/run", { gun, rakipler: rakipler.length ? rakipler : null }).then(r => r.data),
};

// ── LLM Configs ───────────────────────────────────────────────────────────────

export const llmConfigApi = {
  listele:  ()                                               => http.get<LLMConfig[]>("/llm-configs/").then(r => r.data),
  ekle:     (d: { provider_name: string; model_name: string; api_key: string; base_url?: string }) =>
    http.post<LLMConfig>("/llm-configs/", d).then(r => r.data),
  aktifle:  (id: number)                                     => http.post(`/llm-configs/${id}/activate`).then(r => r.data),
  sil:      (id: number)                                     => http.delete(`/llm-configs/${id}`),
  aktifAl:  ()                                               => http.get("/llm-configs/active").then(r => r.data),
};

// ── Competitors (legacy /competitors endpoint, RSS-based) ─────────────────────

export const rakipFirmaApi = {
  listele:  () => http.get<RakipFirma[]>("/competitors/").then(r => r.data),
  analiz:   (sektor = "") =>
    http.post<RakipFirma[]>("/competitors/analyze", null, { params: { sektor } }).then(r => r.data),
  ekle:     (d: RakipFirmaOlustur) =>
    http.post<RakipFirma>("/competitors/", d).then(r => r.data),
  guncelle: (id: number, d: Partial<RakipFirma>) =>
    http.patch<RakipFirma>(`/competitors/${id}`, d).then(r => r.data),
  sil:      (id: number) => http.delete(`/competitors/${id}`),
};

// ── Tenant Competitors ────────────────────────────────────────────────────────

export const tenantRakipApi = {
  listele:  (sadece_aktif = true) =>
    http.get<TenantRakip[]>("/tenant-competitors/", { params: { sadece_aktif } }).then(r => r.data),
  analizBaslat: (sektor = "")    =>
    http.post("/tenant-competitors/analyze", null, { params: { sektor } }).then(r => r.data),
  ekle:     (d: { ad: string; aciklama?: string; bolge?: string; sektor?: string }) =>
    http.post<TenantRakip>("/tenant-competitors/", d).then(r => r.data),
  guncelle: (id: number, d: Partial<TenantRakip>) =>
    http.patch<TenantRakip>(`/tenant-competitors/${id}`, d).then(r => r.data),
  sil:      (id: number)         => http.delete(`/tenant-competitors/${id}`),
};
