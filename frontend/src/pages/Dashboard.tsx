import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp, TrendingDown, Minus, FileText, Users, Newspaper,
} from "lucide-react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { statsApi, type Istatistik, type TimelineVeri } from "@/lib/api";
import { formatTarihSaat } from "@/lib/utils";

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
