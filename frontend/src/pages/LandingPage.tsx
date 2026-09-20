import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LanguageToggle } from "../components/layout/LanguageToggle";
import { useViewMode } from "../components/layout/ViewContext";
import { useCitizenLanguage } from "../lib/i18n/CitizenLanguage";
import { strings } from "../lib/i18n/citizenStrings";

function useInView<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, inView };
}

type StepKind = "describe" | "locate" | "resolve";

function StepIcon({ kind }: { kind: StepKind }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  return (
    <svg {...common}>
      {kind === "describe" && (
        <>
          <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z" />
          <path d="M14 2v5h5" />
          <path d="M9 13h6" />
          <path d="M9 17h6" />
        </>
      )}
      {kind === "locate" && (
        <>
          <path d="M12 21s-7-5.3-7-11a7 7 0 0 1 14 0c0 5.7-7 11-7 11z" />
          <circle cx="12" cy="10" r="2.5" />
        </>
      )}
      {kind === "resolve" && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M8.5 12.2l2.4 2.4 4.6-4.8" />
        </>
      )}
    </svg>
  );
}

function HeroBackdrop() {
  const archHoles: string[] = [];
  for (let x = 356; x <= 844; x += 36) {
    archHoles.push(`M${x} 470 V 434 A 7 7 0 0 1 ${x + 14} 434 V 470 Z`);
  }
  const holes = archHoles.join(" ");

  return (
    <svg
      aria-hidden="true"
      className="landing-hero-bg"
      viewBox="0 0 1200 560"
      preserveAspectRatio="xMidYMax slice"
      focusable="false"
    >
      <g fill="currentColor" fillRule="evenodd">
        <path
          d={`M350 425 H850 V470 H350 Z ${holes}`}
        />
        <path d="M350 418 H850 V425 H350 Z" />
        <path d="M410 350 H790 V418 H410 Z" />
        <path d="M480 292 H720 V350 H480 Z" />
        <path d="M540 240 H660 V292 H540 Z" />
        <path
          d="M540 240 C 520 225, 520 190, 550 155 C 572 122, 592 98, 600 84 C 608 98, 628 122, 650 155 C 680 190, 680 225, 660 240 Z"
        />
        <path d="M598.5 60 H601.5 V84 H598.5 Z" />
        <path d="M480 292 C 470 278, 496 252, 510 244 C 524 252, 550 278, 540 292 Z" />
        <path d="M660 292 C 650 278, 676 252, 690 244 C 704 252, 730 278, 720 292 Z" />
        <path d="M286 340 H322 V470 H286 Z" />
        <path d="M280 340 H328 V348 H280 Z" />
        <path d="M286 340 C 278 326, 292 302, 304 292 C 316 302, 330 326, 322 340 Z" />
        <path d="M302.5 268 H305.5 V292 H302.5 Z" />
        <path d="M878 340 H914 V470 H878 Z" />
        <path d="M872 340 H920 V348 H872 Z" />
        <path d="M878 340 C 870 326, 884 302, 896 292 C 908 302, 922 326, 914 340 Z" />
        <path d="M894.5 268 H897.5 V292 H894.5 Z" />
      </g>
      <g fill="currentColor">
        <circle cx="600" cy="54" r="5" />
        <circle cx="510" cy="238" r="3" />
        <circle cx="690" cy="238" r="3" />
        <circle cx="304" cy="260" r="3.5" />
        <circle cx="896" cy="260" r="3.5" />
      </g>
    </svg>
  );
}

function CornerMotif({ className }: { className: string }) {
  const strokes = [
    "M0 0 L185 77",
    "M0 0 L141 141",
    "M0 0 L77 185",
    "M0 0 L200 0",
    "M0 0 L0 200",
  ];
  const arcs = ["220", "170", "120", "70"].map((r) => `M${r} 0 A${r} ${r} 0 0 0 0 ${r}`);

  return (
    <svg
      aria-hidden="true"
      className={`landing-motif ${className}`}
      viewBox="0 0 220 220"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      focusable="false"
    >
      {strokes.map((d) => (
        <path key={d} d={d} />
      ))}
      {arcs.map((d) => (
        <path key={d} d={d} />
      ))}
      <circle cx="141" cy="141" r="3" />
      <circle cx="185" cy="77" r="3" />
      <circle cx="77" cy="185" r="3" />
    </svg>
  );
}

export default function LandingPage() {
  const { setView } = useViewMode();
  const { lang } = useCitizenLanguage();
  const navigate = useNavigate();
  const dict = strings[lang];

  const stepsView = useInView<HTMLOListElement>();

  const enterCitizen = () => {
    setView("citizen");
    navigate("/route");
  };

  const enterAdmin = () => {
    setView("admin");
    navigate("/admin");
  };

  return (
    <div className="landing-page">
      <header className="citizen-bar">
        <div className="citizen-brand">
          <div className="brand-mark" />
          <div>
            <div className="brand-title">{dict.brandTitle}</div>
            <div className="brand-sub">{dict.brandSub}</div>
          </div>
        </div>
        <div className="citizen-bar-actions">
          <LanguageToggle />
        </div>
      </header>

      <main className="landing-content">
        <section className="landing-hero">
          <div className="landing-bg">
            <HeroBackdrop />
            <CornerMotif className="landing-motif--tl" />
            <CornerMotif className="landing-motif--tr" />
            <CornerMotif className="landing-motif--bl" />
            <CornerMotif className="landing-motif--br" />
          </div>
          <div className="landing-hero-content">
            <h1>{dict.brandTitle}</h1>
            <p className="landing-tagline">{dict.landingTagline}</p>
            <p className="landing-intro">{dict.landingIntro}</p>
            <div className="hero-actions">
              <button type="button" className="btn btn-primary btn-lg" onClick={enterCitizen}>
                {dict.ctaReport}
              </button>
              <button type="button" className="btn btn-outline btn-lg" onClick={enterAdmin}>
                {dict.ctaExploreAdmin}
              </button>
            </div>
          </div>
        </section>

        <section className="landing-flow">
          <h2 className="landing-section-title">{dict.landingHowTitle}</h2>
          <ol
            className={`landing-steps landing-reveal${stepsView.inView ? " is-revealed" : ""}`}
            ref={stepsView.ref}
          >
            <li className="landing-step">
              <span className="route-step-no">
                <StepIcon kind="describe" />
              </span>
              <div className="landing-step-text">
                <h3>{dict.stepDescribe}</h3>
                <p>{dict.landingStepDescribeBody}</p>
              </div>
            </li>
            <li className="landing-step">
              <span className="route-step-no">
                <StepIcon kind="locate" />
              </span>
              <div className="landing-step-text">
                <h3>{dict.stepPinLocation}</h3>
                <p>{dict.landingStepPinBody}</p>
              </div>
            </li>
            <li className="landing-step">
              <span className="route-step-no">
                <StepIcon kind="resolve" />
              </span>
              <div className="landing-step-text">
                <h3>{dict.stepResponsible}</h3>
                <p>{dict.landingStepResponsibleBody}</p>
              </div>
            </li>
          </ol>
        </section>
      </main>
    </div>
  );
}