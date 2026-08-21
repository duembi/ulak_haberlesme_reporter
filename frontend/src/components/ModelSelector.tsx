import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bot } from "lucide-react";
import { settingsApi } from "@/lib/api";

type Grup = { label: string; modeller: { id: string; ad: string }[] };

const MODEL_GRUPLARI: Grup[] = [
  {
    label: "Claude",
    modeller: [
      { id: "claude-sonnet-4-6",        ad: "Sonnet 4.6" },
      { id: "claude-haiku-4-5-20251001", ad: "Haiku 4.5"  },
      { id: "claude-opus-4-7",           ad: "Opus 4.7"   },
    ],
  },
  {
    label: "Gemini",
    modeller: [
      { id: "gemini-3.1-pro",        ad: "3.1 Pro"        },
      { id: "gemini-3-flash",        ad: "3 Flash"        },
      { id: "gemini-3.1-flash-lite", ad: "3.1 Flash Lite" },
    ],
  },
  {
    label: "OpenAI",
    modeller: [
      { id: "gpt-5.5",      ad: "GPT 5.5"      },
      { id: "gpt-5.4",      ad: "GPT 5.4"      },
      { id: "gpt-5.4-mini", ad: "GPT 5.4 Mini" },
    ],
  },
  {
    label: "Meta",
    modeller: [
      { id: "llama3", ad: "LLaMA 3" },
    ],
  },
  {
    label: "xAI",
    modeller: [
      { id: "grok-4.3", ad: "GROK 4.3" },
    ],
  },
];

const TUM_MODELLER = MODEL_GRUPLARI.flatMap(g => g.modeller);

function modelAdiBul(id: string): string {
  const m = TUM_MODELLER.find(m => m.id === id);
  if (!m) return id;
  const g = MODEL_GRUPLARI.find(g => g.modeller.some(x => x.id === id));
  return g ? `${g.label} ${m.ad}` : m.ad;
}

export default function ModelSelector() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["settings-model"],
    queryFn:  settingsApi.modelAl,
  });

  const guncelle = useMutation({
    mutationFn: settingsApi.modelGuncelle,
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["settings-model"] }),
  });

  const secilenModel = data?.model ?? "claude-sonnet-4-6";

  return (
    <div className="px-3 py-3 border-t border-white/10">
      <div className="flex items-center gap-2 px-1 mb-2">
        <Bot size={13} className="text-slate-500" />
        <span className="text-xs text-slate-500 uppercase tracking-wide font-medium">
          AI Modeli
        </span>
      </div>

      <div className="relative">
        <select
          disabled={isLoading || guncelle.isPending}
          value={secilenModel}
          onChange={e => guncelle.mutate(e.target.value)}
          className={`
            w-full appearance-none bg-white/5 text-white text-xs rounded-lg
            px-3 py-2 border border-white/10 cursor-pointer
            focus:outline-none focus:ring-1 focus:ring-brand-500
            hover:bg-white/10 transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          {MODEL_GRUPLARI.map(grup => (
            <optgroup key={grup.label} label={grup.label}
              style={{ background: "#0F172A", color: "#94A3B8" }}>
              {grup.modeller.map(m => (
                <option key={m.id} value={m.id}
                  style={{ background: "#0F172A", color: "#F1F5F9" }}>
                  {m.ad}
                </option>
              ))}
            </optgroup>
          ))}
        </select>

        {/* Ok ikonu */}
        <div className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2">
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1L5 5L9 1" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>

      {/* Seçilen modelin tam adı */}
      <p className="text-slate-600 text-[10px] px-1 mt-1.5 truncate">
        {guncelle.isPending ? "Kaydediliyor…" : modelAdiBul(secilenModel)}
      </p>
    </div>
  );
}
