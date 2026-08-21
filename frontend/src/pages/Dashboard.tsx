import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp, TrendingDown, Minus, FileText, Users, Newspaper, X, ExternalLink,
} from "lucide-react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { statsApi, type Istatistik, type TimelineVeri, type HaberOzet } from "@/lib/api";
import { formatTarihSaat, formatTarih, cn } from "@/lib/utils";

function StatCard({
  label, value, icon: Icon, color, sub,
}: { label: string; value: number | string; icon: React.ElementType; color: string; sub?: string }) {
  return (
    <div className="card p-6 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-slate-500 text-sm">{label}</p>
        <p className="text-2xl font-semibold text-slate-900 mt-0.5">{value}</p>
        {sub && <p className="text-slate-400 text-xs mt-1">{sub}</p>}
      </div>
    </div>
  );
}

const SENTIMENT_COLORS: Record<string, string> = {
  olumlu: "#16A34A",
  olumsuz: "#DC2626",
  nötr:   "#6B7280",
};

// ── Timeline Chart ────────────────────────────────────────────────────────────

function TimelineChart() {
  const { data = [], isLoading } = useQuery<TimelineVeri[]>({
    queryKey: ["timeline"],
    queryFn: () => statsApi.timeline(30),
    refetchInterval: 60_000,
  });

  const formatted = data.map(d => ({
    ...d,
    gun: d.gun.slice(5), // "2024-01-15" → "01-15"
  }));

  return (
    <div className="card p-6">
      <h2 className="text-base font-semibold text-slate-900 mb-1">Haber Trendi</h2>
      <p className="text-xs text-slate-400 mb-4">Son 30 gün — günlük toplam ve olumsuz haber</p>
      {isLoading ? (
        <div className="h-48 bg-slate-50 rounded-lg animate-pulse" />
      ) : data.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-slate-400 text-sm">
          Henüz yeterli veri yok
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={formatted} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis
              dataKey="gun"
              tick={{ fontSize: 11, fill: "#94A3B8" }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#94A3B8" }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{ borderRadius: "8px", border: "1px solid #E2E8F0", fontSize: "12px" }}
              formatter={(v, name) => [
                v,
                name === "toplam" ? "Toplam haber" : "Olumsuz haber",
              ]}
            />
            <Legend
              formatter={(v) => (
                <span className="text-slate-600 text-xs">
                  {v === "toplam" ? "Toplam haber" : "Olumsuz haber"}
                </span>
              )}
            />
            <Line
              type="monotone"
              dataKey="toplam"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="olumsuz"
              stroke="#EF4444"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// ── ULAK kartı + dönem popup'ı ──────────────────────────────────────────────────

const SENTIMENT_BADGE: Record<string, string> = {
  olumlu: "bg-green-100 text-green-700",
  olumsuz: "bg-red-100 text-red-700",
  nötr: "bg-slate-100 text-slate-600",
};

const DONEMLER = [
  { key: "bugun", label: "Bugün", gun: 1 },
  { key: "hafta", label: "Bu Hafta", gun: 7 },
  { key: "ay", label: "Bu Ay", gun: 30 },
  { key: "sene", label: "Bu Sene", gun: 365 },
] as const;

type Donem = (typeof DONEMLER)[number];

function HaberPopup({ donem, onKapat }: { donem: Donem; onKapat: () => void }) {
  const { data = [], isLoading } = useQuery<HaberOzet[]>({
    queryKey: ["dashboard-haberler", donem.gun],
    queryFn: () => statsApi.haberler(donem.gun),
  });

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
            <h2 className="text-base font-semibold text-slate-900">ULAK — {donem.label}</h2>
            <p className="text-slate-500 text-sm mt-0.5">
              {isLoading ? "Yükleniyor…" : `${data.length} haber`}
            </p>
          </div>
          <button onClick={onKapat} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-2.5">
          {isLoading ? (
            [...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-50 rounded-xl animate-pulse" />
            ))
          ) : data.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-10">Bu dönemde haber bulunamadı.</p>
          ) : (
            data.map((h) => (
              <a
                key={h.id}
                href={h.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start justify-between gap-3 p-3.5 rounded-xl border border-slate-100 hover:border-brand-300 hover:bg-brand-50/50 transition-colors group"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 group-hover:text-brand-700 line-clamp-2">
                    {h.baslik}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-slate-400 flex-wrap">
                    {h.kaynak && <span>{h.kaynak}</span>}
                    {h.tarih && <span>· {formatTarih(h.tarih)}</span>}
                    {h.sentiment && (
                      <span className={cn("px-1.5 py-0.5 rounded-full font-medium", SENTIMENT_BADGE[h.sentiment] ?? "bg-slate-100 text-slate-600")}>
                        {h.sentiment}
                      </span>
                    )}
                  </div>
                </div>
                <ExternalLink size={14} className="text-slate-300 group-hover:text-brand-500 shrink-0 mt-1" />
              </a>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function UlakKarti() {
  const [acikDonem, setAcikDonem] = useState<Donem | null>(null);

  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center shrink-0 overflow-hidden">
          <img src="/logo.svg" alt="" className="w-full h-full object-contain p-1" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-slate-900">ULAK</h2>
          <p className="text-xs text-slate-400">Dönem seçin, o dönemin haberlerini görün</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {DONEMLER.map((d) => (
          <button
            key={d.key}
            onClick={() => setAcikDonem(d)}
            className="py-2.5 rounded-lg text-sm font-medium border border-slate-200 text-slate-600 hover:bg-brand-50 hover:border-brand-300 hover:text-brand-700 transition-colors"
          >
            {d.label}
          </button>
        ))}
      </div>
      {acikDonem && <HaberPopup donem={acikDonem} onKapat={() => setAcikDonem(null)} />}
    </div>
  );
}

// ── Ana bileşen ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery<Istatistik>({
    queryKey: ["stats"],
    queryFn: statsApi.al,
    refetchInterval: 30_000,
  });

  if (isLoading) return <Skeleton />;
  if (isError || !data) return <ErrorState />;

  const total = data.olumlu + data.olumsuz + data.notr || 1;
  const pieData = [
    { name: "Olumlu", value: data.olumlu },
    { name: "Olumsuz", value: data.olumsuz },
    { name: "Nötr",   value: data.notr   },
  ].filter(d => d.value > 0);

  const sentimentOrani = Math.round((data.olumlu / total) * 100);

  return (
    <div className="space-y-6 animate-slide-up">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">Son 7 günün medya özeti</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Toplam Haber" value={data.toplam_haber}
          icon={Newspaper} color="bg-brand-600" sub="Son 7 gün" />
        <StatCard label="Olumlu" value={`%${sentimentOrani}`}
          icon={TrendingUp} color="bg-green-600" sub={`${data.olumlu} haber`} />
        <StatCard label="Olumsuz" value={`%${Math.round((data.olumsuz / total) * 100)}`}
          icon={TrendingDown} color="bg-red-600" sub={`${data.olumsuz} haber`} />
        <StatCard label="Nötr" value={`%${Math.round((data.notr / total) * 100)}`}
          icon={Minus} color="bg-slate-500" sub={`${data.notr} haber`} />
      </div>

      {/* ULAK kartı — dönem bazlı haber popup'ı */}
      <UlakKarti />

      {/* Timeline grafik — tam genişlik */}
      <TimelineChart />

      {/* Alt satır: Pie + Özet */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-4">Sentiment Dağılımı</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%"
                innerRadius={60} outerRadius={90} paddingAngle={3} dataKey="value">
                {pieData.map((entry) => (
                  <Cell key={entry.name}
                    fill={SENTIMENT_COLORS[entry.name.toLowerCase()] ?? "#94A3B8"} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [`${v} haber`, ""]}
                contentStyle={{ borderRadius: "8px", border: "1px solid #E2E8F0", fontSize: "13px" }}
              />
              <Legend formatter={(v) => <span className="text-slate-600 text-sm">{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-4">
          <div className="card p-6 flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
              <FileText size={20} className="text-indigo-600" />
            </div>
            <div>
              <p className="text-slate-500 text-sm">Toplam Rapor</p>
              <p className="text-2xl font-semibold text-slate-900 mt-0.5">{data.toplam_rapor}</p>
              <p className="text-slate-400 text-xs mt-1">
                Son rapor: {formatTarihSaat(data.son_rapor_tarihi)}
              </p>
            </div>
          </div>

          <div className="card p-6 flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center shrink-0">
              <Users size={20} className="text-purple-600" />
            </div>
            <div>
              <p className="text-slate-500 text-sm">Aktif Alıcı</p>
              <p className="text-2xl font-semibold text-slate-900 mt-0.5">{data.aktif_alici}</p>
              <p className="text-slate-400 text-xs mt-1">Mail listesinde kayıtlı</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-slate-200 rounded-lg" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <div key={i} className="card h-28 bg-slate-50" />)}
      </div>
      <div className="card h-56 bg-slate-50" />
    </div>
  );
}

function ErrorState() {
  return (
    <div className="card p-12 text-center">
      <p className="text-slate-500 text-sm">API'ye bağlanılamadı. Giriş yapmanız gerekiyor olabilir.</p>
    </div>
  );
}
