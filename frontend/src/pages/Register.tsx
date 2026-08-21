import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "", sifre: "", ad_soyad: "", kurum_adi: "",
  });
  const [hata, setHata] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);

  const domain = form.email.includes("@") ? form.email.split("@")[1] : "";

  const emailDegistir = (val: string) =>
    setForm({ ...form, email: val.replace(/ı/g, "i").replace(/İ/g, "I") });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setHata("");
    if (form.sifre.length < 8) {
      setHata("Şifre en az 8 karakter olmalı.");
      return;
    }
    setYukleniyor(true);
    try {
      const data = await authApi.kayit(form);
      login(data.access_token, data.kullanici);
      navigate("/");
    } catch (err: any) {
      setHata(err.response?.data?.detail ?? "Kayıt başarısız. Lütfen tekrar deneyin.");
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
          Kurumsal e-posta adresinizle kayıt olun. Domain bilginiz
          otomatik olarak kurum hesabınıza bağlanır.
        </p>
      </div>

      {/* Sağ panel */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center mb-4 lg:hidden overflow-hidden shadow">
              <img src="/logo.jpg" alt="Logo" className="w-full h-full object-contain" />
            </div>
            <h2 className="text-2xl font-semibold text-slate-900">Hesap Oluştur</h2>
            <p className="text-slate-500 text-sm mt-1">Kurumsal e-posta adresinizle kayıt olun</p>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">Ad Soyad</label>
              <input
                className="input"
                placeholder="Ahmet Yılmaz"
                value={form.ad_soyad}
                onChange={e => setForm({ ...form, ad_soyad: e.target.value })}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="label">Kurumsal E-posta</label>
              <input
                className="input"
                type="email"
                placeholder="ahmet@kurum.com.tr"
                value={form.email}
                onChange={e => emailDegistir(e.target.value)}
                required
              />
              {domain && (
                <p className="text-xs text-slate-400 mt-1">
                  Kurum domain'i: <span className="font-mono text-brand-600">{domain}</span>
                </p>
              )}
            </div>
            <div>
              <label className="label">Kurum Adı <span className="text-slate-400">(opsiyonel)</span></label>
              <input
                className="input"
                placeholder="Kurum adı (boş bırakılırsa domain kullanılır)"
                value={form.kurum_adi}
                onChange={e => setForm({ ...form, kurum_adi: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Şifre</label>
              <input
                className="input"
                type="password"
                placeholder="En az 8 karakter"
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
              {yukleniyor ? "Kayıt oluşturuluyor…" : "Kayıt Ol"}
            </button>
          </form>

          <p className="text-sm text-slate-500 text-center mt-6">
            Zaten hesabınız var mı?{" "}
            <Link to="/login" className="text-brand-600 hover:underline font-medium">
              Giriş Yap
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
