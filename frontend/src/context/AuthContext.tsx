import { createContext, useContext, useEffect, useState } from "react";
import { http } from "@/lib/api";

interface Kullanici {
  id: number;
  email: string;
  ad_soyad: string;
  rol: string;
  tenant_id: number;
  tenant_adi?: string;
  tenant_domain?: string;
}

interface Palet {
  brand_600: string; brand_700: string; brand_500: string;
  brand_50:  string; brand_100: string; brand_200: string; brand_800: string;
  sidebar:   string;
  bg_base:   string; bg_card:   string; bg_input:  string; bg_hover:  string;
  text_main: string; text_sub:  string; text_muted: string; border: string;
}

interface Branding { light: Palet; dark: Palet; }

interface AuthContextType {
  user: Kullanici | null;
  token: string | null;
  isDark: boolean;
  login: (token: string, user: Kullanici) => Promise<void>;
  logout: () => void;
  toggleDark: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

function applyPalet(palet: Palet) {
  const r = document.documentElement;
  r.style.setProperty("--brand-50",    palet.brand_50);
  r.style.setProperty("--brand-100",   palet.brand_100);
  r.style.setProperty("--brand-200",   palet.brand_200);
  r.style.setProperty("--brand-500",   palet.brand_500);
  r.style.setProperty("--brand-600",   palet.brand_600);
  r.style.setProperty("--brand-700",   palet.brand_700);
  r.style.setProperty("--brand-800",   palet.brand_800);
  r.style.setProperty("--sidebar",     palet.sidebar);
  r.style.setProperty("--bg-base",     palet.bg_base);
  r.style.setProperty("--bg-card",     palet.bg_card);
  r.style.setProperty("--bg-input",    palet.bg_input);
  r.style.setProperty("--bg-hover",    palet.bg_hover);
  r.style.setProperty("--text-main",   palet.text_main);
  r.style.setProperty("--text-sub",    palet.text_sub);
  r.style.setProperty("--text-muted",  palet.text_muted);
  r.style.setProperty("--border",      palet.border);
}

function resetPalet() {
  const keys = [
    "--brand-50","--brand-100","--brand-200","--brand-500",
    "--brand-600","--brand-700","--brand-800","--sidebar",
    "--bg-base","--bg-card","--bg-input","--bg-hover",
    "--text-main","--text-sub","--text-muted","--border",
  ];
  keys.forEach(k => document.documentElement.style.removeProperty(k));
}

function setDarkClass(dark: boolean) {
  document.documentElement.classList.toggle("dark", dark);
}

async function refreshBrandingFromServer(tenantId: number): Promise<Branding> {
  const res = await http.post<Branding>("/auth/branding/refresh");
  localStorage.setItem(`brand_${tenantId}`, JSON.stringify(res.data));
  return res.data;
}

async function fetchBrandingCached(tenantId: number): Promise<Branding> {
  const res = await http.get<Branding>("/auth/branding");
  localStorage.setItem(`brand_${tenantId}`, JSON.stringify(res.data));
  return res.data;
}

function getCachedBranding(tenantId: number): Branding | null {
  try {
    const raw = localStorage.getItem(`brand_${tenantId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.light && parsed?.dark) return parsed as Branding;
    return null;
  } catch { return null; }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser]         = useState<Kullanici | null>(null);
  const [token, setToken]       = useState<string | null>(null);
  const [isDark, setIsDark]     = useState(false);
  const [branding, setBranding] = useState<Branding | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const dark = localStorage.getItem("dark_mode") === "1";
    setIsDark(dark);
    setDarkClass(dark);

    const savedToken = localStorage.getItem("auth_token");
    const savedUser  = localStorage.getItem("auth_user");

    if (savedToken && savedUser) {
      try {
        const parsedUser: Kullanici = JSON.parse(savedUser);
        setToken(savedToken);
        setUser(parsedUser);

        // localStorage cache'i hemen uygula (flash önleme)
        const cached = getCachedBranding(parsedUser.tenant_id);
        if (cached) {
          setBranding(cached);
          applyPalet(dark ? cached.dark : cached.light);
        }

        // Arka planda DB cache'den taze renkleri çek
        fetchBrandingCached(parsedUser.tenant_id)
          .then(b => {
            setBranding(b);
            applyPalet(dark ? b.dark : b.light);
          })
          .catch(() => {})
          .finally(() => setIsLoading(false));
        return;
      } catch {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (newToken: string, newUser: Kullanici) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("auth_user", JSON.stringify(newUser));

    const dark = localStorage.getItem("dark_mode") === "1";
    try {
      // Login'de her zaman LLM'den taze renk üret (DB cache'i de günceller)
      const b = await refreshBrandingFromServer(newUser.tenant_id);
      setBranding(b);
      applyPalet(dark ? b.dark : b.light);
    } catch {
      // LLM başarısız olursa varsayılan CSS değerleri kalır
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setBranding(null);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    resetPalet();
    setDarkClass(false);
    setIsDark(false);
  };

  const toggleDark = () => {
    const next = !isDark;
    setIsDark(next);
    setDarkClass(next);
    localStorage.setItem("dark_mode", next ? "1" : "0");
    if (branding) applyPalet(next ? branding.dark : branding.light);
  };

  return (
    <AuthContext.Provider value={{ user, token, isDark, login, logout, toggleDark, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
