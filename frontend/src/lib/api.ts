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

export interface Istatistik {
  toplam_haber: number;
}

export interface TimelineVeri {
  gun: string;
  toplam: number;
  olumsuz: number;
}

export interface HaberOzet {
  id: number;
  baslik: string;
  url: string;
  kaynak: string | null;
  tarih: string | null;
  kategori: string | null;
}

export interface RakipKartHaberi {
  baslik: string;
  url: string;
  kaynak: string;
  tarih: string | null;
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

export interface PipelineDurumu {
  calisiyor: boolean;
  baslangic_zamani: string | null;
  bitis_zamani: string | null;
  sonuc: "basarili" | "hata" | null;
  hata: string | null;
}

export interface LinkedInGonderi {
  baslik: string;
  ozet: string;
  url: string;
  tag?: string | null;
}

export interface FirmaSonucu {
  haberler: RakipKartHaberi[];
  linkedin: LinkedInGonderi[];
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  kayit: (data: { email: string; sifre: string; ad_soyad: string; kurum_adi?: string }) =>
    http.post("/auth/register", data).then(r => r.data),
  giris: (email: string, sifre: string) =>
    http.post("/auth/login", { email, sifre }).then(r => r.data),
  me: () => http.get("/auth/me").then(r => r.data),
};

// ── Stats ─────────────────────────────────────────────────────────────────────

export const statsApi = {
  al:           ()                             => http.get<Istatistik>("/stats").then(r => r.data),
  timeline:     (gun: number)                  => http.get<TimelineVeri[]>("/stats/timeline", { params: { gun } }).then(r => r.data),
  haberler:     (gun: number)                  => http.get<HaberOzet[]>("/stats/news", { params: { gun } }).then(r => r.data),
  rakipKartlar: ()                             => http.get<Record<string, Record<string, number>>>("/stats/rakip-kartlar").then(r => r.data),
  rakipHaberler:(firma: string, gun: number)   => http.get<RakipKartHaberi[]>("/stats/rakip-haberler", { params: { firma, gun } }).then(r => r.data),
  haberSayilari:()                             => http.get<Record<string, number>>("/stats/news-counts").then(r => r.data),
  linkedin:     (firma: string, gun = 30)      => http.get<LinkedInGonderi[]>("/stats/linkedin", { params: { firma, gun } }).then(r => r.data),
};

// ── Pipeline ──────────────────────────────────────────────────────────────────

export const pipelineApi = {
  durum:    ()                => http.get<PipelineDurumu>("/pipeline/status").then(r => r.data),
  baslat:   (gun: number)     => http.post("/pipeline/run", { gun }).then(r => r.data),
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
  haberler: (adlar: string[], gun = 7) =>
    http.post<Record<string, FirmaSonucu>>("/tenant-competitors/haberler", { adlar, gun }).then(r => r.data),
};

// ── Yönetim Kurulu / Yönetim ────────────────────────────────────────────────────

export interface YonetimKisi {
  id: number;
  tenant_id: number;
  ad_soyad: string;
  unvan: string;
  grup: "kurul" | "yonetim" | "ust_kademe";
  foto_url: string;
  linkedin_url?: string | null;
  kaynak: string;
  aktif: boolean;
  olusturuldu_at: string;
  guncellendi_at: string;
}

export interface YonetimDegisiklik {
  id: number;
  ad_soyad: string;
  tur: "eklendi" | "ayrildi" | "unvan_degisti";
  detay: string;
  tarih: string;
}

export const yonetimApi = {
  listele:      ()          => http.get<YonetimKisi[]>("/yonetim/").then(r => r.data),
  senkronize:   ()          => http.post<YonetimKisi[]>("/yonetim/senkronize").then(r => r.data),
  degisiklikler:()          => http.get<YonetimDegisiklik[]>("/yonetim/degisiklikler").then(r => r.data),
  haberler:     (kisiId: number, gun = 180) =>
    http.get<FirmaSonucu>(`/yonetim/${kisiId}/haberler`, { params: { gun } }).then(r => r.data),
  ustKademeKesif: () => http.post<YonetimKisi[]>("/yonetim/ust-kademe/kesif").then(r => r.data),
  ustKademeSil:   (kisiId: number) => http.delete(`/yonetim/ust-kademe/${kisiId}`),
};
