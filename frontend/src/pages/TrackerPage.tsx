import { useEffect, useMemo, useState } from "react";

import { DemoDayFilter } from "../components/filters/DemoDayFilter";
import { useAuth } from "../context/AuthContext";
import { useDemoDay } from "../context/DemoDayContext";
import { ApiError, trackerOverviewGuest, trackerOverviewUser } from "../lib/api";
import type { TrackerOverviewResponse, TrackerOverviewSlot } from "../types/api";

const DAY_ORDER: Record<string, number> = {
  Monday: 1,
  Tuesday: 2,
  Wednesday: 3,
  Thursday: 4,
  Friday: 5,
  Saturday: 6,
  Sunday: 7,
};

function formatCalories(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "N/A";
  }
  return `${value}`;
}

function mealSortValue(meal: string): number {
  if (meal === "Breakfast") {
    return 1;
  }
  if (meal === "Lunch") {
    return 2;
  }
  if (meal === "Dinner") {
    return 3;
  }
  return 99;
}

function groupedSchedule(schedule: TrackerOverviewSlot[]): Array<{ day: string; slots: TrackerOverviewSlot[] }> {
  const map = new Map<string, TrackerOverviewSlot[]>();
  for (const slot of schedule) {
    const slotsForDay = map.get(slot.day_of_week) ?? [];
    slotsForDay.push(slot);
    map.set(slot.day_of_week, slotsForDay);
  }
  const groups = Array.from(map.entries()).map(([day, slots]) => ({
    day,
    slots: slots.slice().sort((a, b) => mealSortValue(a.meal) - mealSortValue(b.meal)),
  }));
  groups.sort((a, b) => (DAY_ORDER[a.day] ?? 99) - (DAY_ORDER[b.day] ?? 99));
  return groups;
}

export default function TrackerPage() {
  const { user } = useAuth();
  const { selectedDay, dayOverride, setSelectedDay } = useDemoDay();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<TrackerOverviewResponse | null>(null);

  async function loadTrackerData() {
    setLoading(true);
    setError(null);
    try {
      const response = user ? await trackerOverviewUser(dayOverride) : await trackerOverviewGuest(dayOverride);
      setOverview(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to load tracker data.");
      }
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTrackerData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, dayOverride]);

  const emptyFavorites = useMemo(() => {
    return !loading && !error && overview !== null && overview.favorites.length === 0;
  }, [loading, error, overview]);

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-border-default bg-surface-white p-6 md:p-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-[-0.01em] text-ink-primary">Tracker</h1>
            <p className="mt-2 text-sm text-ink-3">
              {user
                ? "Account tracker is active. Cards below are tied to your account favorites."
                : "Guest tracker is active. Sign in to keep tracker data tied to your account."}
            </p>
          </div>
          <DemoDayFilter selectedDay={selectedDay} onChange={setSelectedDay} />
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void loadTrackerData()}
            disabled={loading}
            className="rounded-button border border-border-default px-4 py-2 text-sm text-ink-2 transition hover:border-brand-blue hover:text-brand-blue disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Refreshing..." : "Refresh Tracker"}
          </button>
          {overview ? (
            <span className="mono-value text-xs text-ink-4">Applied day: {overview.applied_day}</span>
          ) : null}
        </div>

        {error ? (
          <div className="mt-4 rounded-input border border-status-error-text bg-status-error-bg px-3 py-3 text-sm text-status-error-text">
            <p>{error}</p>
            <button
              type="button"
              onClick={() => void loadTrackerData()}
              className="mt-2 text-xs font-medium underline-offset-4 transition hover:underline"
            >
              Retry
            </button>
          </div>
        ) : null}
      </section>

      {loading ? (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="rounded-card border border-border-default bg-surface-white p-5">
              <div className="h-4 w-44 rounded-input border border-border-default bg-surface-page" />
              <div className="mt-3 h-3 w-28 rounded-input border border-border-default bg-surface-page" />
              <div className="mt-5 h-16 rounded-input border border-border-default bg-surface-page" />
            </div>
          ))}
        </section>
      ) : null}

      {emptyFavorites ? (
        <section className="rounded-card border border-border-default bg-surface-white p-6 text-center">
          <p className="text-[15px] text-ink-2">No favorites yet.</p>
          <p className="mt-2 text-sm text-ink-3">
            Star items from Home and they will show up here with day-by-day schedule cards.
          </p>
        </section>
      ) : null}

      {!loading && !error && overview && overview.favorites.length > 0 ? (
        <section className="grid grid-cols-1 gap-4">
          {overview.favorites.map((favorite) => {
            const grouped = groupedSchedule(favorite.schedule);
            return (
              <article
                key={favorite.favorite_id}
                className="rounded-card border border-border-default bg-surface-white p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h2 className="text-lg font-semibold text-ink-primary">{favorite.item_name}</h2>
                  <span
                    className={`rounded-pill px-3 py-1 text-xs font-semibold uppercase tracking-[0.04em] ${
                      favorite.available_today
                        ? "bg-status-open-bg text-status-open-text"
                        : "bg-status-warning-bg text-status-warning-text"
                    }`}
                  >
                    {favorite.available_today ? "Available today" : "Not today"}
                  </span>
                </div>

                <div className="mt-4 rounded-input border border-border-default bg-surface-page p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-4">
                    {overview.applied_day}
                  </p>
                  {favorite.today_slots.length === 0 ? (
                    <p className="mt-2 text-sm text-ink-3">
                      Not today. Check the schedule below for the next available meals.
                    </p>
                  ) : (
                    <div className="mt-2 flex flex-col gap-2">
                      {favorite.today_slots.map((slot, index) => (
                        <div
                          key={`${favorite.favorite_id}-today-${index}-${slot.meal}-${slot.dining_hall}`}
                          className="rounded-input border border-border-default bg-surface-white px-3 py-2"
                        >
                          <p className="text-sm font-medium text-ink-2">
                            {slot.meal} - {slot.dining_hall}
                          </p>
                          <p className="mono-value mt-1 text-xs text-ink-3">
                            {slot.protein_grams}g protein | Calories: {formatCalories(slot.calories)}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.06em] text-ink-4">Full schedule</p>
                  {favorite.schedule.length === 0 ? (
                    <p className="mt-2 text-sm text-ink-3">
                      No schedule rows found yet for this favorite in the current dining dataset.
                    </p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {grouped.map((group) => (
                        <div key={`${favorite.favorite_id}-${group.day}`} className="rounded-input border border-border-default p-3">
                          <p className="text-sm font-semibold text-ink-2">{group.day}</p>
                          <div className="mt-2 space-y-1.5">
                            {group.slots.map((slot, index) => (
                              <p key={`${favorite.favorite_id}-${group.day}-${index}`} className="text-sm text-ink-3">
                                {slot.meal} - {slot.dining_hall} ({slot.protein_grams}g, Calories:{" "}
                                {formatCalories(slot.calories)})
                              </p>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      ) : null}
    </div>
  );
}
