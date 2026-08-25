import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  LogOut, ChevronDown, Building2, Users,
  Sun, Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { useState } from "react";

export default function Sidebar() {
  const { user, logout, isDark, toggleDark } = useAuth();
  const navigate = useNavigate();
  const [userMenuAcik, setUserMenuAcik] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="fixed inset-y-0 left-0 w-60 bg-sidebar flex flex-col z-30">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
        <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shrink-0 overflow-hidden">
          <img src="/logo.jpg" alt="Logo" className="w-full h-full object-contain" />
        </div>
        <div>
          <p className="text-white text-sm font-semibold leading-tight">
            {user?.tenant_adi || "Medya İstihbarat"}
          </p>
          <p className="text-slate-400 text-xs leading-tight">
            {user?.tenant_domain || "SaaS Platform"}
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {/* Dashboard */}
        <NavLink to="/" end
          className={({ isActive }) => cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
            isActive ? "bg-brand-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
          )}>
          <LayoutDashboard size={17} /> Dashboard
        </NavLink>

        {/* Yönetim Kurulu */}
        <NavLink to="/yonetim-kurulu"
          className={({ isActive }) => cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
            isActive ? "bg-brand-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
          )}>
          <Users size={17} /> Yönetim Kurulu
        </NavLink>

        {/* Rakip Firmalar */}
        <NavLink to="/rakip-firmalar"
          className={({ isActive }) => cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
            isActive ? "bg-brand-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
          )}>
          <Building2 size={17} /> Rakip Firmalar
        </NavLink>
      </nav>

      {/* Kullanıcı menüsü */}
      <div className="px-3 py-3 border-t border-white/10">
        <button
          onClick={() => setUserMenuAcik(a => !a)}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:bg-white/5 hover:text-white transition-all"
        >
          <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center shrink-0">
            <span className="text-white text-xs font-bold">
              {user?.ad_soyad?.charAt(0).toUpperCase() ?? "?"}
            </span>
          </div>
          <div className="flex-1 text-left min-w-0">
            <p className="text-xs font-medium text-white truncate">{user?.ad_soyad}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <ChevronDown
            size={14}
            className={cn("transition-transform shrink-0", userMenuAcik && "rotate-180")}
          />
        </button>

        {userMenuAcik && (
          <div className="mt-1 mx-1">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <LogOut size={15} />
              Çıkış Yap
            </button>
          </div>
        )}
      </div>

      {/* Dark mode toggle */}
      <div className="px-3 py-2 border-t border-white/10">
        <button
          onClick={toggleDark}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-white/5 hover:text-white transition-all"
        >
          {isDark
            ? <Sun size={15} className="text-amber-400" />
            : <Moon size={15} />}
          <span className="text-xs font-medium">
            {isDark ? "Açık Mod" : "Koyu Mod"}
          </span>
          <div className={cn(
            "ml-auto w-8 h-4 rounded-full transition-colors relative shrink-0",
            isDark ? "bg-brand-600" : "bg-white/20"
          )}>
            <div className={cn(
              "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform",
              isDark ? "translate-x-4" : "translate-x-0.5"
            )} />
          </div>
        </button>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-white/10">
        <p className="text-slate-500 text-xs">v2.0.0 · Multi-Tenant SaaS</p>
      </div>
    </aside>
  );
}
