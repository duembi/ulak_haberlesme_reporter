import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Network, ChevronDown, ChevronUp, Save, CheckSquare, Square } from "lucide-react";
import { http } from "@/lib/api";
import { cn } from "@/lib/utils";


interface TagBilgi {
  tag: string;
  aciklama: string;
}

interface TagYanit {
  kategoriler: Record<string, TagBilgi[]>;
  secili: string[];
}

function TagGrubu({
  kategori,
  tagler,
  secili,
  toggle,
}: {
  kategori: string;
  tagler: TagBilgi[];
  secili: Set<string>;
  toggle: (tag: string) => void;
}) {
  const [acik, setAcik] = useState(true);
  const seciliSayi = tagler.filter(t => secili.has(t.tag)).length;
  const hepsiSecili = seciliSayi === tagler.length;

  const toggleHepsi = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hepsiSecili) tagler.forEach(t => secili.has(t.tag) && toggle(t.tag));
    else tagler.forEach(t => !secili.has(t.tag) && toggle(t.tag));
  };

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
        onClick={() => setAcik(a => !a)}
      >
        <div className="flex items-center gap-3">
          <span onClick={toggleHepsi} className="text-slate-400 hover:text-brand-600 transition-colors">
            {hepsiSecili
              ? <CheckSquare size={17} className="text-brand-600" />
              : <Square size={17} />
            }
          </span>
          <span className="text-sm font-semibold text-slate-800">{kategori}</span>
          <span className={cn(
            "text-xs px-2 py-0.5 rounded-full font-medium",
            seciliSayi > 0
              ? "bg-brand-100 text-brand-700"
              : "bg-slate-200 text-slate-500"
          )}>
            {seciliSayi}/{tagler.length}
          </span>
        </div>
        {acik
          ? <ChevronUp size={16} className="text-slate-400" />
          : <ChevronDown size={16} className="text-slate-400" />
        }
      </button>

      {acik && (
        <div className="grid grid-cols-2 gap-2 p-4">
          {tagler.map(({ tag, aciklama }) => (
            <label
              key={tag}
              className="flex items-start gap-2.5 cursor-pointer group p-2 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <input
                type="checkbox"
                className="w-4 h-4 mt-0.5 rounded accent-brand-600 shrink-0"
                checked={secili.has(tag)}
                onChange={() => toggle(tag)}
              />
              <div>
                <p className="text-sm font-semibold text-brand-700 group-hover:text-brand-900 transition-colors">
                  {tag}
                </p>
                <p className="text-xs text-slate-400">{aciklama}</p>
              </div>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LinkedIn() {
  const qc = useQueryClient();
  const [secili, setSecili] = useState<Set<string>>(new Set());
  const [kaydedildi, setKaydedildi] = useState(false);

  const { data, isLoading } = useQuery<TagYanit>({
    queryKey: ["linkedin-tags"],
    queryFn: () => http.get<TagYanit>("/linkedin/tags").then(r => r.data),
  });

  useEffect(() => {
    if (data?.secili) setSecili(new Set(data.secili));
  }, [data]);

  const kaydet = useMutation({
    mutationFn: () =>
      http.post("/linkedin/tags", { secili: [...secili] }).then(r => r.data),
    onSuccess: () => {
      setKaydedildi(true);
      qc.invalidateQueries({ queryKey: ["linkedin-tags"] });
      setTimeout(() => setKaydedildi(false), 2500);
    },
  });

  const toggle = (tag: string) =>
    setSecili(prev => {
      const s = new Set(prev);
      s.has(tag) ? s.delete(tag) : s.add(tag);
      return s;
    });

  const tumTagler = Object.values(data?.kategoriler ?? {}).flat();
  const toplamSecili = secili.size;

  const hepsiniSec = () =>
    setSecili(new Set(tumTagler.map(t => t.tag)));

  const hepsiniTemizle = () => setSecili(new Set());

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Network size={22} className="text-[#0A66C2]" />
            <h1 className="text-2xl font-semibold text-slate-900">LinkedIn Tag Takibi</h1>
          </div>
          <p className="text-slate-500 text-sm">
            Raporda izlemek istediğiniz LinkedIn hashtaglerini seçin.
            Pipeline çalıştığında bu taglerle gönderiler aranacak.
          </p>
        </div>

        <button
          onClick={() => kaydet.mutate()}
          disabled={kaydet.isPending}
          className={cn(
            "btn-primary flex items-center gap-2 px-5 py-2.5 transition-all",
            kaydedildi && "bg-green-600 hover:bg-green-700"
          )}
        >
          <Save size={16} />
          {kaydedildi ? "Kaydedildi!" : "Kaydet"}
        </button>
      </div>

      {/* Özet bar */}
      <div className="card p-4 flex items-center justify-between">
        <div className="flex items-center gap-6 text-sm">
          <span className="text-slate-500">
            Seçili: <strong className="text-brand-700">{toplamSecili}</strong> tag
          </span>
          <span className="text-slate-500">
            Toplam mevcut: <strong className="text-slate-700">{tumTagler.length}</strong>
          </span>
        </div>
        <div className="flex gap-3">
          <button
            className="text-xs text-brand-600 hover:underline font-medium"
            onClick={hepsiniSec}
          >
            Tümünü Seç
          </button>
          <span className="text-slate-300">·</span>
          <button
            className="text-xs text-slate-500 hover:underline"
            onClick={hepsiniTemizle}
          >
            Temizle
          </button>
        </div>
      </div>

      {/* Gruplar */}
      {isLoading ? (
        <div className="text-center py-12 text-slate-400 text-sm">Yükleniyor…</div>
      ) : (
        <div className="space-y-3">
          {Object.entries(data?.kategoriler ?? {}).map(([kategori, tagler]) => (
            <TagGrubu
              key={kategori}
              kategori={kategori}
              tagler={tagler}
              secili={secili}
              toggle={toggle}
            />
          ))}
        </div>
      )}

      {/* Alt bilgi */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <p className="text-xs text-blue-700 leading-relaxed">
          <strong>Nasıl çalışır?</strong> Seçilen her tag için DuckDuckGo üzerinden
          <code className="mx-1 bg-blue-100 px-1 rounded">site:linkedin.com/posts &lt;tag&gt;</code>
          araması yapılır. Bulunan gönderiler Claude ile analiz edilerek PDF rapora eklenir.
        </p>
      </div>
    </div>
  );
}
