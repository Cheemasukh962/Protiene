import type { DemoDaySelection, WeekdayName } from "../types/api";

const DEMO_DAY_STORAGE_KEY = "dprotein_demo_day";

const VALID_WEEKDAYS: WeekdayName[] = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function isWeekday(value: string): value is WeekdayName {
  return VALID_WEEKDAYS.includes(value as WeekdayName);
}

export function loadDemoDaySelection(): DemoDaySelection {
  const raw = sessionStorage.getItem(DEMO_DAY_STORAGE_KEY);
  if (!raw) {
    return "Today";
  }
  if (raw === "Today") {
    return "Today";
  }
  if (isWeekday(raw)) {
    return raw;
  }
  return "Today";
}

export function saveDemoDaySelection(value: DemoDaySelection): void {
  sessionStorage.setItem(DEMO_DAY_STORAGE_KEY, value);
}
