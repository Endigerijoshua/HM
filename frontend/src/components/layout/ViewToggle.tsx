import { useNavigate } from "react-router-dom";
import { useViewMode, type ViewMode } from "./ViewContext";

const OPTIONS: { key: ViewMode; label: string }[] = [
  { key: "citizen", label: "Citizen View" },
  { key: "admin", label: "Admin View" },
];

export function ViewToggle() {
  const { view, setView } = useViewMode();
  const navigate = useNavigate();

  const switchTo = (key: ViewMode) => {
    if (key === view) return;
    setView(key);
    navigate(key === "citizen" ? "/route" : "/admin");
  };

  return (
    <div className="view-toggle" role="tablist" aria-label="Application view">
      {OPTIONS.map((option) => (
        <button
          key={option.key}
          type="button"
          role="tab"
          aria-selected={view === option.key}
          className={`view-toggle-btn${view === option.key ? " active" : ""}`}
          onClick={() => switchTo(option.key)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}