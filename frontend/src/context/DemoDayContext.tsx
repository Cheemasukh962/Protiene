import { createContext, useContext, useMemo, useState } from "react";

import { loadDemoDaySelection, saveDemoDaySelection } from "../lib/demoDayStorage";
import type { DemoDaySelection, WeekdayName } from "../types/api";

interface DemoDayContextValue {
  selectedDay: DemoDaySelection;
  dayOverride: WeekdayName | undefined;
  setSelectedDay: (nextValue: DemoDaySelection) => void;
}

const DemoDayContext = createContext<DemoDayContextValue | null>(null);

function toDayOverride(day: DemoDaySelection): WeekdayName | undefined {
  if (day === "Today") {
    return undefined;
  }
  return day;
}

export function DemoDayProvider({ children }: { children: React.ReactNode }) {
  const [selectedDay, setSelectedDayState] = useState<DemoDaySelection>(() => loadDemoDaySelection());

  function setSelectedDay(nextValue: DemoDaySelection) {
    setSelectedDayState(nextValue);
    saveDemoDaySelection(nextValue);
  }

  const value = useMemo<DemoDayContextValue>(
    () => ({
      selectedDay,
      dayOverride: toDayOverride(selectedDay),
      setSelectedDay,
    }),
    [selectedDay],
  );

  return <DemoDayContext.Provider value={value}>{children}</DemoDayContext.Provider>;
}

export function useDemoDay(): DemoDayContextValue {
  const context = useContext(DemoDayContext);
  if (!context) {
    throw new Error("useDemoDay must be used within DemoDayProvider");
  }
  return context;
}
