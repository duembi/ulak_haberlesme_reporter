import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", sifre: "" });

  const emailDegistir = (val: string) =>
    setForm({ ...form, email: val.replace(/ı/g, "i").replace(/İ/g, "I") });
  const [hata, setHata] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setHata("");
    setYukleniyor(true);
    try {
      const data = await authApi.giris(form.email, form.sifre);
      await login(data.access_token, data.kullanici);
      navigate("/");
    } catch (err: any) {
      setHata(err.response?.data?.detail ?? "Giriş başarısız. Lütfen tekrar deneyin.");
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Sol panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-sidebar flex-col items-center justify-center p-12">
        <div className="w-20 h-20 rounded-2xl bg-white flex items-center justify-center mb-6 overflow-hidden shadow-lg">
          <img src="/logo.jpg" alt="Logo" className="w-full h-full object-contain" />
        </div>
        <h1 className="text-white text-3xl font-bold mb-3">Medya İstihbarat</h1>
        <p className="text-slate-400 text-center max-w-sm">
          Kurumunuza ait haberleri takip edin, rakiplerinizi analiz edin,
          otomatik raporlar oluşturun.
        </p>
      </div>

      {/* Sağ panel */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center mb-4 lg:hidden overflow-hidden shadow">
              <img src="/logo.jpg" alt="Logo" className="w-full h-full object-contain" />
            </div>
            <h2 className="text-2xl font-semibold text-slate-900">Giriş Yap</h2>
            <p className="text-slate-500 text-sm mt-1">Kurumsal hesabınızla devam edin</p>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">E-posta</label>
              <input
                className="input"
                type="email"
                placeholder="ad@kurum.com"
                value={form.email}
                onChange={e => emailDegistir(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="label">Şifre</label>
              <input
                className="input"
                type="password"
                placeholder="••••••••"
                value={form.sifre}
                onChange={e => setForm({ ...form, sifre: e.target.value })}
                required
              />
            </div>

            {hata && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
                {hata}
              </div>
            )}

            <button type="submit" disabled={yukleniyor} className="btn-primary w-full justify-center py-2.5">
              {yukleniyor ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {yukleniyor ? "Tema yükleniyor…" : "Giriş yapılıyor…"}
                </span>
              ) : "Giriş Yap"}
            </button>
          </form>

          <p className="text-sm text-slate-500 text-center mt-6">
            Hesabınız yok mu?{" "}
            <Link to="/register" className="text-brand-600 hover:underline font-medium">
              Kayıt Ol
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
