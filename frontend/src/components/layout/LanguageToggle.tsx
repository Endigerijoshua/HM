import { LANG_LABELS, LANGS } from "../../lib/i18n/citizenStrings";
import { useCitizenLanguage } from "../../lib/i18n/CitizenLanguage";

export function LanguageToggle() {
  const { lang, setLang } = useCitizenLanguage();

  return (
    <div className="lang-toggle" role="group" aria-label="Language">
      {LANGS.map((option) => (
        <button
          key={option}
          type="button"
          className={`lang-toggle-btn${lang === option ? " active" : ""}`}
          aria-pressed={lang === option}
          onClick={() => setLang(option)}
        >
          {LANG_LABELS[option]}
        </button>
      ))}
    </div>
  );
}