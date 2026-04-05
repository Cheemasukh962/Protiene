import { useEffect, useRef, useState } from "react";

import type { DemoDaySelection } from "../../types/api";

const DAY_OPTIONS: DemoDaySelection[] = [
  "Today",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

interface DemoDayFilterProps {
  selectedDay: DemoDaySelection;
  onChange: (nextValue: DemoDaySelection) => void;
}

function FilterIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 6H20" />
      <path d="M7 12H17" />
      <path d="M10 18H14" />
    </svg>
  );
}

export function DemoDayFilter({ selectedDay, onChange }: DemoDayFilterProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handleDocumentClick(event: MouseEvent) {
      if (!containerRef.current) {
        return;
      }
      if (!containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    if (open) {
      document.addEventListener("mousedown", handleDocumentClick);
      return () => {
        document.removeEventListener("mousedown", handleDocumentClick);
      };
    }
    return undefined;
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="inline-flex h-9 items-center gap-2 rounded-pill border border-border-default bg-surface-white px-3 text-sm text-ink-2 transition hover:border-brand-blue hover:text-brand-blue"
      >
        <FilterIcon />
        <span>{selectedDay}</span>
      </button>

      {open ? (
        <div className="absolute right-0 top-11 z-40 w-[200px] rounded-card border border-border-default bg-surface-white p-3 shadow-sm">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-4">
            Demo day
          </p>
          <div className="space-y-1">
            {DAY_OPTIONS.map((day) => (
              <button
                key={day}
                type="button"
                onClick={() => {
                  onChange(day);
                  setOpen(false);
                }}
                className={`w-full rounded-input px-3 py-2 text-left text-sm transition ${
                  selectedDay === day
                    ? "bg-brand-blue text-white"
                    : "text-ink-2 hover:bg-brand-blue-tint hover:text-brand-blue"
                }`}
              >
                {day}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
