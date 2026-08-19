import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/resume", label: "Resume" },
  { to: "/interview", label: "New Interview" },
  { to: "/monitor", label: "Monitoring" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      <header className="bg-indigo-700 text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold">IntelliVue</span>
            <span className="rounded bg-indigo-500 px-2 py-0.5 text-xs">AI Interview</span>
          </div>
          <nav className="flex items-center gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? "bg-indigo-600" : "hover:bg-indigo-600/60"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
            <div className="ml-3 flex items-center gap-2 border-l border-indigo-500 pl-3">
              <span className="text-sm">{user?.name ?? "Guest"}</span>
              <button
                className="rounded-lg bg-indigo-800 px-3 py-1.5 text-xs font-medium hover:bg-indigo-900"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                Log out
              </button>
            </div>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}