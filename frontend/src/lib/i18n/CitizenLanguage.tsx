import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { readStoredLang, storeLang, type Lang } from "./citizenStrings";

interface CitizenLanguageValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
}

const CitizenLanguageContext = createContext<CitizenLanguageValue | null>(null);

export function CitizenLanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(readStoredLang);

  const value = useMemo<CitizenLanguageValue>(
    () => ({
      lang,
      setLang: (next: Lang) => {
        setLang(next);
        storeLang(next);
      },
    }),
    [lang],
  );

  return (
    <CitizenLanguageContext.Provider value={value}>
      {children}
    </CitizenLanguageContext.Provider>
  );
}

export function useCitizenLanguage(): CitizenLanguageValue {
  const ctx = useContext(CitizenLanguageContext);
  if (!ctx) throw new Error("useCitizenLanguage must be used within CitizenLanguageProvider");
  return ctx;
}