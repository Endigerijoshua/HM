export const LANGS = ["en", "kn"] as const;
export type Lang = (typeof LANGS)[number];

export const LANG_LABELS: Record<Lang, string> = { en: "EN", kn: "ಕನ್ನಡ" };

const STORAGE_KEY = "tcdt-language";

export function readStoredLang(): Lang {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "en" || stored === "kn" ? stored : "en";
  } catch {
    return "en";
  }
}

export function storeLang(lang: Lang): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // storage unavailable — language still applies for the session
  }
}

/** Replace {placeholders} in a template string with the given values. */
export function fill(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (match, key) =>
    key in values ? String(values[key]) : match,
  );
}

export interface Dict {
  brandTitle: string;
  brandSub: string;

  // Landing page
  landingTagline: string;
  landingIntro: string;
  landingHowTitle: string;
  landingStepDescribeBody: string;
  landingStepPinBody: string;
  landingStepResponsibleBody: string;
  ctaReport: string;
  ctaExploreAdmin: string;

  pageTitle: string;
  pageSubtitle: string;
  loadingData: string;
  stepDescribe: string;
  stepPinLocation: string;
  stepResponsible: string;
  issueTypeLabel: string;
  onDateLabel: string;
  issuePlaceholder: string;
  jurisdictionCount: string;
  presetsSummary: string;
  presetsDatesLabel: string;
  presetsScenariosLabel: string;
  quickDates: Record<string, string>;
  scenarios: Record<string, string>;
  issueTypeNames: Record<string, string>;
  categoryNames: Record<string, string>;
  gpsIdle: string;
  gpsRequesting: string;
  tryAgain: string;
  locationFrom: string;
  sourceMap: string;
  sourceGps: string;
  sourceManual: string;
  accuracyTemplate: string;
  gpsOutside: string;
  emptyLocationHint: string;
  mapHintRoute: string;
  mapHintChooseIssue: string;
  manualSummary: string;
  latitude: string;
  longitude: string;
  setLocation: string;
  latError: string;
  lngError: string;
  manualHint: string;
  resolveIdle: string;
  resolveBusy: string;
  resolveHintNoIssue: string;
  resolveHintNoLocation: string;
  resultEmpty: string;
  resultPoint: string;
  resultIssue: string;
  resultDate: string;
  resultJurisdiction: string;
  resultWard: string;
  resultVersion: string;
  resultMatchedScope: string;
  resultSla: string;
  slaUnit: string;
  resultRule: string;
  resultEscalationPath: string;
  resultConflictTitle: string;
  resultConflictBody: string;
  resultConflictNote: string;
  resultNoJurisdiction: string;
  resultAudit: string;
  actorAuthority: string;
  actorDepartment: string;
  actorService: string;
  explainTitle: string;
  explainAriaNotResolved: string;
  explainAriaChosen: string;
  explainDecisionBasis: string;
  explainStoppedAt: string;
  explainStoppedAtNames: Record<string, string>;
  explainStoppedReasons: Record<string, string>;
  conflictingRules: string;
  auditId: string;
  ruleId: string;
  checkLabels: Record<string, string>;
  stepNames: Record<string, string>;
  coordsLabel: string;
  versionLabel: string;
  matchedScopeLabel: string;
  slaDays: string;
  ruleIdNum: string;
  escalationSteps: string;
  mapFooter: string;
  advancedSummary: string;
  advancedWhyRoute: string;
  routingStatus: string;
  auditRouting: string;
  rulesCount: string;
  tableRule: string;
  tableScope: string;
  tablePrio: string;
  tableInForce: string;
  tableAuthorityService: string;
  routeExtraSummary: string;
  replayLink: string;
  historyLink: string;
}

const en: Dict = {
  brandTitle: "JanSetu",
  brandSub: "Temporal Civic Jurisdiction Digital Twin (TCJDT)",

  landingTagline: "Your complaint, routed to the right office.",
  landingIntro:
    "Report what's wrong, and JanSetu finds the office responsible — even when ward boundaries change.",
  landingHowTitle: "How it works",
  landingStepDescribeBody: "What's wrong",
  landingStepPinBody: "Where it is",
  landingStepResponsibleBody: "Who must act",
  ctaReport: "Report an issue",
  ctaExploreAdmin: "Explore admin tools",

  pageTitle: "Citizen Routing",
  pageSubtitle:
    "Tell us what the issue is, where it is, and when — we'll tell you who must act.",
  loadingData: "Loading Mysuru map data…",

  stepDescribe: "Describe the issue",
  stepPinLocation: "Pin the location",
  stepResponsible: "The responsible authority",

  // Step 1
  issueTypeLabel: "Issue type",
  onDateLabel: "On this date",
  issuePlaceholder: "Select an issue…",
  jurisdictionCount: "{count} jurisdictions in force on {date}",
  presetsSummary: "Example presets",
  presetsDatesLabel: "Dates",
  presetsScenariosLabel: "Scenarios",

  quickDates: {
    "2023-06-01": "V1 · DELIM-2020",
    "2024-01-05": "Gap · no jurisdiction",
    "2024-06-01": "V2 · DELIM-2024",
  },

  scenarios: {
    "Pothole · W-05": "Pothole · W-05",
    "Heritage maintenance · W-05": "Heritage maintenance · W-05",
    "Garbage collection · V1/V2 flip": "Garbage collection · V1/V2 flip",
    "Construction waste · unresolved": "Construction waste · unresolved",
  },

  // Display names for backend issue-type codes and categories (values stay as
  // backend enum codes; only the shown label is translated).
  issueTypeNames: {
    garbage: "Garbage / solid waste",
    garbage_collection: "Garbage Collection (legacy code)",
    overflowing_bin: "Overflowing public bin",
    illegal_dumping: "Illegal dumping of waste",
    street_sweeping: "Street Sweeping (legacy code)",
    public_toilet: "Public Toilet (legacy code)",
    pothole: "Pothole on city road",
    road_repair: "Road Repair (legacy code)",
    road_damage: "Road surface damage",
    drain_cleaning: "Drain Cleaning (legacy code)",
    drainage: "Blocked storm-water drain",
    water_supply: "Water supply interruption",
    sewage: "Sewage leak / overflow",
    sewage_overflow: "Sewage Overflow (legacy code)",
    streetlight: "Street light not working",
    street_light: "Street Light (legacy code)",
    heritage_maintenance: "Heritage zone maintenance",
    layout_approval: "Layout approval inquiry",
    sh_repair: "State Highway Repair",
    nh_repair: "National Highway Repair",
    power_outage: "Electricity outage",
    construction_waste: "Construction waste on public land",
    public_property_damage: "Public property damage",
  },

  categoryNames: {
    sanitation: "Sanitation",
    roads: "Roads",
    water: "Water",
    lighting: "Lighting",
    heritage: "Heritage",
    planning: "Planning",
    highways: "Highways",
    utility: "Utility",
    construction: "Construction",
    public_property: "Public property",
  },

  // Step 2
  gpsIdle: "Use My Current Location",
  gpsRequesting: "Getting your location…",
  tryAgain: "Try again",
  locationFrom: "Location from {source}",
  sourceMap: "the map",
  sourceGps: "your current location",
  sourceManual: "manual entry",
  accuracyTemplate: "· accuracy ±{accuracy} m",
  gpsOutside:
    "Your current location is outside the supported Mysuru civic dataset. The point is still valid — routing will report that no supported jurisdiction covers it.",
  emptyLocationHint: "Tap the map below, or use your current location.",
  mapHintRoute:
    'Click any street or location on the map to route "{issueType}" on {onDate}.',
  mapHintChooseIssue: "Select an issue type first, then click a location on the map.",

  manualSummary: "Enter coordinates manually",
  latitude: "Latitude",
  longitude: "Longitude",
  setLocation: "Set location",
  latError: "Latitude must be a number between -90 and 90.",
  lngError: "Longitude must be a number between -180 and 180.",
  manualHint:
    "Use coordinates you read from the map or a GPS device. The point must be inside the networked city area shown on the map.",

  resolveIdle: "Resolve Responsibility",
  resolveBusy: "Resolving responsibility…",
  resolveHintNoIssue: "Select an issue type above first.",
  resolveHintNoLocation: "Choose a location to enable routing.",

  // Step 3
  resultEmpty:
    "No result yet — describe the issue, pin a location, then press Resolve.",

  resultPoint: "Point",
  resultIssue: "Issue",
  resultDate: "Date",
  resultJurisdiction: "Jurisdiction",
  resultWard: "Ward",
  resultVersion: "Version",
  resultMatchedScope: "Matched scope",
  resultSla: "SLA",
  slaUnit: "days",
  resultRule: "Rule",
  resultEscalationPath: "Escalation path",
  resultConflictTitle: "Responsibility conflict",
  resultConflictBody: "Two equal-priority rules both matched and disagree on ownership:",
  resultConflictNote: "An authority must break the tie before the issue can be routed.",
  resultNoJurisdiction:
    "No supported civic jurisdiction covers this location on the selected date. Try a point inside a Mysuru ward on the map above.",
  resultAudit: "Audit: routing.resolve #{id}",
  actorAuthority: "Authority",
  actorDepartment: "Department",
  actorService: "Service",

  // Explanation panel
  explainTitle: "Why was this routed here?",
  explainAriaNotResolved: "Why this route was not resolved",
  explainAriaChosen: "Why this route was chosen",
  explainDecisionBasis: "Decision basis",
  explainStoppedAt: "Resolution stopped at {step}.",
  explainStoppedAtNames: {
    jurisdiction: "Temporal Jurisdiction",
    rule: "Routing Rule",
    issue: "Issue",
    date: "Date",
    resolution: "Resolution",
  },
  explainStoppedReasons: {
    tie: "Two or more equal-priority rules matched and disagree on ownership.",
    noJurisdiction: "No jurisdiction covers this point on the requested date.",
    unknownIssue: "The issue type is not registered in the decision table.",
    invalidDate: "The requested date is outside the supported routing window.",
    fallback: "The request could not be resolved.",
  },
  conflictingRules: "Conflicting rules matched:",
  auditId: "Decision / audit ID:",
  ruleId: "Decision-table rule id:",
  checkLabels: {
    coordinates: "Valid coordinates",
    jurisdiction: "Jurisdiction found for requested date",
    issue: "Issue type matched",
    rule: "Responsibility rule matched",
    service: "Service resolved",
  },
  stepNames: {
    location: "Location",
    temporalJurisdiction: "Temporal Jurisdiction",
    wardArea: "Ward / Area",
    authority: "Responsible Authority",
    department: "Department",
    service: "Service",
    routingRule: "Routing Rule",
    escalationPath: "Escalation Path",
  },
  coordsLabel: "Coordinates:",
  versionLabel: "· Version: {version}",
  matchedScopeLabel: "· matched scope: {scope}",
  slaDays: "· SLA {days} days",
  ruleIdNum: "· rule id #{id}",
  escalationSteps: "· steps: {steps}",
  mapFooter:
    "Map: probe marker and {jurisdiction} boundary highlight use exactly these coordinates.",

  // Advanced / engine details
  advancedSummary: "Engine details · graph & decision rules",
  advancedWhyRoute: "Why this route? · Responsibility Graph",
  routingStatus: "Routing status:",
  auditRouting: "Routing audit #{id}",
  rulesCount: "{count} rule(s) in force for {issue} on {date}",
  tableRule: "Rule",
  tableScope: "Scope",
  tablePrio: "Prio",
  tableInForce: "In force",
  tableAuthorityService: "Authority → Service",

  // Result footer
  routeExtraSummary: "Explore further",
  replayLink: "Explore this location historically →",
  historyLink: "Open in Historical Explorer",
};

const kn: Dict = {
  brandTitle: "ಜನಸೇತು",
  brandSub: "ತಾತ್ಕಾಲಿಕ ನಾಗರಿಕ ವ್ಯಾಪ್ತಿ ಡಿಜಿಟಲ್ ಟ್ವಿನ್ (TCJDT)",

  landingTagline: "ನಿಮ್ಮ ದೂರು, ಸರಿಯಾದ ಕಚೇರಿಗೆ.",
  landingIntro:
    "ಸಮಸ್ಯೆ ಏನೆಂದು ವರದಿ ಮಾಡಿ, ಜನಸೇತು ಜವಾಬ್ದಾರಿಯ ಕಚೇರಿಯನ್ನು ಪತ್ತೆ ಮಾಡುತ್ತದೆ — ವಾರ್ಡ್ ಗಡಿಗಳು ಬದಲಾದರೂ ಸಹ.",
  landingHowTitle: "ಇದು ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ",
  landingStepDescribeBody: "ಸಮಸ್ಯೆ ಏನು",
  landingStepPinBody: "ಎಲ್ಲಿದೆ",
  landingStepResponsibleBody: "ಯಾರು ಕಾರ್ಯನಿರ್ವಹಿಸಬೇಕು",
  ctaReport: "ಸಮಸ್ಯೆ ವರದಿ ಮಾಡಿ",
  ctaExploreAdmin: "ನಿರ್ವಾಹಕ ಪರಿಕರಗಳನ್ನು ಅನ್ವೇಷಿಸಿ",

  pageTitle: "ನಾಗರಿಕ ಸೇವಾ ಮಾರ್ಗದರ್ಶನ",
  pageSubtitle:
    "ಸಮಸ್ಯೆ ಏನು, ಎಲ್ಲಿ ಮತ್ತು ಯಾವಾಗ ಎಂದು ಹೇಳಿ — ಯಾರು ಕಾರ್ಯನಿರ್ವಹಿಸಬೇಕು ಎಂದು ನಾವು ತಿಳಿಸುತ್ತೇವೆ.",
  loadingData: "ಮೈಸೂರು ನಕ್ಷೆ ಡೇಟಾ ಲೋಡ್ ಆಗುತ್ತಿದೆ…",

  stepDescribe: "ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ",
  stepPinLocation: "ಸ್ಥಳ ಗುರುತಿಸಿ",
  stepResponsible: "ಜವಾಬ್ದಾರಿ ಪ್ರಾಧಿಕಾರ",

  issueTypeLabel: "ಸಮಸ್ಯೆ ಪ್ರಕಾರ",
  onDateLabel: "ಈ ದಿನಾಂಕದಂದು",
  issuePlaceholder: "ಸಮಸ್ಯೆಯನ್ನು ಆಯ್ಕೆ ಮಾಡಿ…",
  jurisdictionCount: "{count} ವ್ಯಾಪ್ತಿಗಳು {date} ರಂದು ಜಾರಿಯಲ್ಲಿವೆ",
  presetsSummary: "ಉದಾಹರಣೆ ಮಾದರಿಗಳು",
  presetsDatesLabel: "ದಿನಾಂಕಗಳು",
  presetsScenariosLabel: "ಸನ್ನಿವೇಶಗಳು",

  quickDates: {
    "2023-06-01": "V1 · DELIM-2020",
    "2024-01-05": "ಅಂತರ · ವ್ಯಾಪ್ತಿ ಇಲ್ಲ",
    "2024-06-01": "V2 · DELIM-2024",
  },

  scenarios: {
    "Pothole · W-05": "ರಸ್ತೆ ಗುಂಡಿ · W-05",
    "Heritage maintenance · W-05": "ಪರಂಪರೆ ನಿರ್ವಹಣೆ · W-05",
    "Garbage collection · V1/V2 flip": "ಕಸ ಸಂಗ್ರಹ · V1/V2 ಬದಲಾವಣೆ",
    "Construction waste · unresolved": "ನಿರ್ಮಾಣ ತ್ಯಾಜ್ಯ · ಬಗೆಹರಿಯದ",
  },

  issueTypeNames: {
    garbage: "ಕಸ / ಘನ ತ್ಯಾಜ್ಯ",
    garbage_collection: "ಕಸ ಸಂಗ್ರಹ (ಹಳೆಯ ಕೋಡ್)",
    overflowing_bin: "ತುಂಬಿರುವ ಸಾರ್ವಜನಿಕ ಬಿನ್",
    illegal_dumping: "ಅಕ್ರಮ ತ್ಯಾಜ್ಯ ಸುರಿಯುವಿಕೆ",
    street_sweeping: "ರಸ್ತೆ ಗುಡಿಸುವಿಕೆ (ಹಳೆಯ ಕೋಡ್)",
    public_toilet: "ಸಾರ್ವಜನಿಕ ಶೌಚಾಲಯ (ಹಳೆಯ ಕೋಡ್)",
    pothole: "ರಸ್ತೆಯಲ್ಲಿ ಗುಂಡಿ",
    road_repair: "ರಸ್ತೆ ದುರಸ್ತಿ (ಹಳೆಯ ಕೋಡ್)",
    road_damage: "ರಸ್ತೆ ಮೇಲ್ಮೈ ಹಾನಿ",
    drain_cleaning: "ಚರಂಡಿ ಸ್ವಚ್ಛತೆ (ಹಳೆಯ ಕೋಡ್)",
    drainage: "ಮುಚ್ಚಿರುವ ಮಳೆನೀರು ಚರಂಡಿ",
    water_supply: "ನೀರು ಸರಬರಾಜು ಅಡಚಣೆ",
    sewage: "ಚರಂಡಿ ಸೋರಿಕೆ / ಉಕ್ಕುವಿಕೆ",
    sewage_overflow: "ಚರಂಡಿ ಉಕ್ಕುವಿಕೆ (ಹಳೆಯ ಕೋಡ್)",
    streetlight: "ಕೆಲಸ ಮಾಡದ ಸ್ಟ್ರೀಟ್ ದೀಪ",
    street_light: "ಸ್ಟ್ರೀಟ್ ದೀಪ (ಹಳೆಯ ಕೋಡ್)",
    heritage_maintenance: "ಪರಂಪರೆ ಪ್ರದೇಶ ನಿರ್ವಹಣೆ",
    layout_approval: "ಲೇಔಟ್ ಅನುಮೋದನೆ ವಿಚಾರಣೆ",
    sh_repair: "ರಾಜ್ಯ ಹೆದ್ದಾರಿ ದುರಸ್ತಿ",
    nh_repair: "ರಾಷ್ಟ್ರೀಯ ಹೆದ್ದಾರಿ ದುರಸ್ತಿ",
    power_outage: "ವಿದ್ಯುತ್ ಸರಬರಾಜು ಅಡಚಣೆ",
    construction_waste: "ಸಾರ್ವಜನಿಕ ಜಾಗದಲ್ಲಿ ನಿರ್ಮಾಣ ತ್ಯಾಜ್ಯ",
    public_property_damage: "ಸಾರ್ವಜನಿಕ ಆಸ್ತಿ ಹಾನಿ",
  },

  categoryNames: {
    sanitation: "ನೈರ್ಮಲ್ಯ",
    roads: "ರಸ್ತೆಗಳು",
    water: "ನೀರು",
    lighting: "ದೀಪ",
    heritage: "ಪರಂಪರೆ",
    planning: "ಯೋಜನೆ",
    highways: "ಹೆದ್ದಾರಿಗಳು",
    utility: "ಸಾರ್ವಜನಿಕ ಸೇವೆಗಳು",
    construction: "ನಿರ್ಮಾಣ",
    public_property: "ಸಾರ್ವಜನಿಕ ಆಸ್ತಿ",
  },

  gpsIdle: "ನನ್ನ ಪ್ರಸ್ತುತ ಸ್ಥಳ ಬಳಸಿ",
  gpsRequesting: "ನಿಮ್ಮ ಸ್ಥಳ ಪಡೆಯಲಾಗುತ್ತಿದೆ…",
  tryAgain: "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
  locationFrom: "{source} ಮೂಲದ ಸ್ಥಳ",
  sourceMap: "ನಕ್ಷೆ",
  sourceGps: "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಸ್ಥಳ",
  sourceManual: "ಹಸ್ತಚಾಲಿತ ನಮೂದು",
  accuracyTemplate: "· ನಿಖರತೆ ±{accuracy} ಮೀ",
  gpsOutside:
    "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಸ್ಥಳವು ಮೈಸೂರು ನಾಗರಿಕ ದತ್ತಾಂಶದ ವ್ಯಾಪ್ತಿಯ ಹೊರಗಿದೆ. ಬಿಂದುವು ಇನ್ನೂ ಮಾನ್ಯ — ಯಾವುದೇ ಅಧಿಕಾರ ವ್ಯಾಪ್ತಿ ಕಂಡುಬರುವುದಿಲ್ಲ ಎಂದು ಮಾರ್ಗದರ್ಶನ ತಿಳಿಸುತ್ತದೆ.",
  emptyLocationHint: "ಕೆಳಗಿನ ನಕ್ಷೆಯಲ್ಲಿ ಟ್ಯಾಪ್ ಮಾಡಿ, ಅಥವಾ ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಸ್ಥಳವನ್ನು ಬಳಸಿ.",
  mapHintRoute:
    '"{issueType}" ಅನ್ನು {onDate} ರಂದು ಮಾರ್ಗಗೊಳಿಸಲು ನಕ್ಷೆಯಲ್ಲಿ ಯಾವುದೇ ರಸ್ತೆ ಅಥವಾ ಸ್ಥಳವನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ.',
  mapHintChooseIssue: "ಮೊದಲು ಸಮಸ್ಯೆ ಪ್ರಕಾರವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ, ನಂತರ ನಕ್ಷೆಯಲ್ಲಿ ಸ್ಥಳ ಕ್ಲಿಕ್ ಮಾಡಿ.",

  manualSummary: "ನಿರ್ದೇಶಾಂಕಗಳನ್ನು ಹಸ್ತಚಾಲಿತವಾಗಿ ನಮೂದಿಸಿ",
  latitude: "ಅಕ್ಷಾಂಶ",
  longitude: "ರೇಖಾಂಶ",
  setLocation: "ಸ್ಥಳ ನಿಗದಿ",
  latError: "ಅಕ್ಷಾಂಶವು -90 ಮತ್ತು 90 ರ ನಡುವಿನ ಸಂಖ್ಯೆಯಾಗಿರಬೇಕು.",
  lngError: "ರೇಖಾಂಶವು -180 ಮತ್ತು 180 ರ ನಡುವಿನ ಸಂಖ್ಯೆಯಾಗಿರಬೇಕು.",
  manualHint:
    "ನಕ್ಷೆ ಅಥವಾ GPS ಸಾಧನದಿಂದ ಓದಿದ ನಿರ್ದೇಶಾಂಕಗಳನ್ನು ಬಳಸಿ. ಬಿಂದುವು ನಕ್ಷೆಯಲ್ಲಿ ತೋರುವ ಸಂಪರ್ಕಿತ ನಗರ ಪ್ರದೇಶದ ಒಳಗೆ ಇರಬೇಕು.",

  resolveIdle: "ಜವಾಬ್ದಾರಿ ನಿರ್ಧರಿಸಿ",
  resolveBusy: "ಜವಾಬ್ದಾರಿ ನಿರ್ಧರಿಸಲಾಗುತ್ತಿದೆ…",
  resolveHintNoIssue: "ಮೊದಲು ಮೇಲಿನ ಸಮಸ್ಯೆ ಪ್ರಕಾರವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ.",
  resolveHintNoLocation: "ಮಾರ್ಗದರ್ಶನ ಸಕ್ರಿಯಗೊಳಿಸಲು ಸ್ಥಳ ಆಯ್ಕೆ ಮಾಡಿ.",

  resultEmpty:
    "ಇನ್ನೂ ಫಲಿತಾಂಶವಿಲ್ಲ — ಸಮಸ್ಯೆ ವಿವರಿಸಿ, ಸ್ಥಳ ಗುರುತಿಸಿ, ನಂತರ «ಜವಾಬ್ದಾರಿ ನಿರ್ಧರಿಸಿ» ಒತ್ತಿರಿ.",

  resultPoint: "ಬಿಂದು",
  resultIssue: "ಸಮಸ್ಯೆ",
  resultDate: "ದಿನಾಂಕ",
  resultJurisdiction: "ಅಧಿಕಾರ ವ್ಯಾಪ್ತಿ",
  resultWard: "ವಾರ್ಡ್",
  resultVersion: "ಆವೃತ್ತಿ",
  resultMatchedScope: "ಹೊಂದಾಣಿಕೆಯ ವ್ಯಾಪ್ತಿ",
  resultSla: "SLA",
  slaUnit: "ದಿನಗಳು",
  resultRule: "ನಿಯಮ",
  resultEscalationPath: "ಮೇಲ್ದರ್ಜೆ ಹಾದಿ",
  resultConflictTitle: "ಜವಾಬ್ದಾರಿ ಸಂಘರ್ಷ",
  resultConflictBody:
    "ಎರಡು ಸಮಾನ ಆದ್ಯತೆಯ ನಿಯಮಗಳು ಹೊಂದಾಣಿಕೆಯಾಗಿ ಮಾಲೀಕತ್ವದಲ್ಲಿ ಭಿನ್ನವಾಗಿವೆ:",
  resultConflictNote:
    "ಸಮಸ್ಯೆಯನ್ನು ಮಾರ್ಗಗೊಳಿಸುವ ಮೊದಲು ಪ್ರಾಧಿಕಾರವು ಸಮಾನತೆಯನ್ನು ಭೇದಿಸಬೇಕು.",
  resultNoJurisdiction:
    "ಯಾವುದೇ ಬೆಂಬಲಿತ ನಾಗರಿಕ ವ್ಯಾಪ್ತಿಯು ಆಯ್ಕೆ ಮಾಡಿದ ದಿನಾಂಕದಲ್ಲಿ ಈ ಸ್ಥಳವನ್ನು ಆವರಿಸುವುದಿಲ್ಲ. ಮೇಲಿನ ನಕ್ಷೆಯಲ್ಲಿ ಮೈಸೂರು ವಾರ್ಡ್ ಒಳಗಿನ ಬಿಂದುವನ್ನು ಪ್ರಯತ್ನಿಸಿ.",
  resultAudit: "ಆಡಿಟ್: routing.resolve #{id}",
  actorAuthority: "ಪ್ರಾಧಿಕಾರ",
  actorDepartment: "ಇಲಾಖೆ",
  actorService: "ಸೇವೆ",

  explainTitle: "ಇದು ಯಾಕೆ ಇಲ್ಲಿಗೆ ಮಾರ್ಗಗೊಳಿಸಲಾಗಿದೆ?",
  explainAriaNotResolved: "ಈ ಮಾರ್ಗ ಯಾಕೆ ಪರಿಹಾರವಾಗಲಿಲ್ಲ",
  explainAriaChosen: "ಈ ಮಾರ್ಗ ಯಾಕೆ ಆಯ್ಕೆಯಾಯಿತು",
  explainDecisionBasis: "ನಿರ್ಧಾರದ ಆಧಾರ",
  explainStoppedAt: "ಪರಿಹಾರವು {step} ನಲ್ಲಿ ನಿಂತಿತು.",
  explainStoppedAtNames: {
    jurisdiction: "ಕಾಲಾನುಕ್ರಮ ವ್ಯಾಪ್ತಿ",
    rule: "ಮಾರ್ಗದರ್ಶನ ನಿಯಮ",
    issue: "ಸಮಸ್ಯೆ",
    date: "ದಿನಾಂಕ",
    resolution: "ಪರಿಹಾರ",
  },
  explainStoppedReasons: {
    tie: "ಎರಡು ಅಥವಾ ಹೆಚ್ಚು ಸಮಾನ ಆದ್ಯತೆಯ ನಿಯಮಗಳು ಹೊಂದಾಣಿಕೆಯಾಗಿ ಮಾಲೀಕತ್ವದಲ್ಲಿ ಭಿನ್ನವಾಗಿವೆ.",
    noJurisdiction: "ಅಭ್ಯರ್ಥಿಸಿದ ದಿನಾಂಕದಲ್ಲಿ ಯಾವುದೇ ವ್ಯಾಪ್ತಿಯು ಈ ಬಿಂದುವನ್ನು ಆವರಿಸುವುದಿಲ್ಲ.",
    unknownIssue: "ಸಮಸ್ಯೆ ಪ್ರಕಾರವು ನಿರ್ಧಾರ ಕೋಷ್ಟಕದಲ್ಲಿ ನೋಂದಾಯಿಸಲಾಗಿಲ್ಲ.",
    invalidDate: "ಅಭ್ಯರ್ಥಿಸಿದ ದಿನಾಂಕವು ಬೆಂಬಲಿತ ಮಾರ್ಗದರ್ಶನ ವಿಂಡೋದ ಹೊರಗಿದೆ.",
    fallback: "ವಿನಂತಿಯನ್ನು ಪರಿಹರಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.",
  },
  conflictingRules: "ಸಂಘರ್ಷದ ನಿಯಮಗಳು ಹೊಂದಾಣಿಕೆಯಾದವು:",
  auditId: "ನಿರ್ಧಾರ / ಆಡಿಟ್ ID:",
  ruleId: "ನಿರ್ಧಾರ-ಕೋಷ್ಟಕ ನಿಯಮ ID:",
  checkLabels: {
    coordinates: "ಮಾನ್ಯ ನಿರ್ದೇಶಾಂಕಗಳು",
    jurisdiction: "ಅಭ್ಯರ್ಥಿಸಿದ ದಿನಾಂಕಕ್ಕೆ ವ್ಯಾಪ್ತಿ ದೊರಕಿದೆ",
    issue: "ಸಮಸ್ಯೆ ಪ್ರಕಾರ ಹೊಂದಾಣಿಕೆ",
    rule: "ಜವಾಬ್ದಾರಿ ನಿಯಮ ಹೊಂದಾಣಿಕೆ",
    service: "ಸೇವೆ ಪರಿಹರಿಸಲಾಗಿದೆ",
  },
  stepNames: {
    location: "ಸ್ಥಳ",
    temporalJurisdiction: "ಕಾಲಾನುಕ್ರಮ ವ್ಯಾಪ್ತಿ",
    wardArea: "ವಾರ್ಡ್ / ಪ್ರದೇಶ",
    authority: "ಜವಾಬ್ದಾರಿ ಪ್ರಾಧಿಕಾರ",
    department: "ಇಲಾಖೆ",
    service: "ಸೇವೆ",
    routingRule: "ಮಾರ್ಗದರ್ಶನ ನಿಯಮ",
    escalationPath: "ಮೇಲ್ದರ್ಜೆ ಹಾದಿ",
  },
  coordsLabel: "ನಿರ್ದೇಶಾಂಕಗಳು:",
  versionLabel: "· ಆವೃತ್ತಿ: {version}",
  matchedScopeLabel: "· ಹೊಂದಾಣಿಕೆ ವ್ಯಾಪ್ತಿ: {scope}",
  slaDays: "· SLA {days} ದಿನಗಳು",
  ruleIdNum: "· ನಿಯಮ ID #{id}",
  escalationSteps: "· ಹಂತಗಳು: {steps}",
  mapFooter:
    "ನಕ್ಷೆ: ಪ್ರೋಬ್ ಗುರುತು ಮತ್ತು {jurisdiction} ಗಡಿ ಹೈಲೈಟ್ ನಿಖರವಾಗಿ ಈ ನಿರ್ದೇಶಾಂಕಗಳನ್ನು ಬಳಸುತ್ತವೆ.",

  advancedSummary: "ಎಂಜಿನ್ ವಿವರಗಳು · ಗ್ರಾಫ್ ಮತ್ತು ನಿರ್ಧಾರ ನಿಯಮಗಳು",
  advancedWhyRoute: "ಏಕೆ ಈ ಮಾರ್ಗ? · ಜವಾಬ್ದಾರಿ ಗ್ರಾಫ್",
  routingStatus: "ಮಾರ್ಗದರ್ಶನ ಸ್ಥಿತಿ:",
  auditRouting: "ಮಾರ್ಗದರ್ಶನ ಆಡಿಟ್ #{id}",
  rulesCount: "{count} ನಿಯಮ(ಗಳು) {issue} ಗೆ {date} ರಂದು ಜಾರಿಯಲ್ಲಿವೆ",
  tableRule: "ನಿಯಮ",
  tableScope: "ವ್ಯಾಪ್ತಿ",
  tablePrio: "ಆದ್ಯತೆ",
  tableInForce: "ಜಾರಿ",
  tableAuthorityService: "ಪ್ರಾಧಿಕಾರ → ಸೇವೆ",

  routeExtraSummary: "ಮತ್ತಷ್ಟು ಅನ್ವೇಷಿಸಿ",
  replayLink: "ಈ ಸ್ಥಳದ ಇತಿಹಾಸ ಅನ್ವೇಷಿಸಿ →",
  historyLink: "ಐತಿಹಾಸಿಕ ಶೋಧಕದಲ್ಲಿ ತೆರೆಯಿರಿ",
};

export const strings: Record<Lang, Dict> = { en, kn };