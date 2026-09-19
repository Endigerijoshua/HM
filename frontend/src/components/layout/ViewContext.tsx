import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type ViewMode = "citizen" | "admin";

const STORAGE_KEY = "tcdt-view-mode";

interface ViewContextValue {
  view: ViewMode;
  setView: (view: ViewMode) => void;
}

const ViewContext = createContext<ViewContextValue | null>(null);

export function ViewProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<ViewMode>(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "admin" || stored === "citizen" ? stored : "citizen";
  });

  const value = useMemo<ViewContextValue>(
    () => ({
      view,
      setView: (next: ViewMode) => {
        setView(next);
        window.localStorage.setItem(STORAGE_KEY, next);
      },
    }),
    [view],
  );

  return <ViewContext.Provider value={value}>{children}</ViewContext.Provider>;
}

export function useViewMode(): ViewContextValue {
  const ctx = useContext(ViewContext);
  if (!ctx) throw new Error("useViewMode must be used within ViewProvider");
  return ctx;
}