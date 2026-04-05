import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { DemoDayFilter } from "../components/filters/DemoDayFilter";
import { useAuth } from "../context/AuthContext";
import { useDemoDay } from "../context/DemoDayContext";
import {
  ApiError,
  deleteFavoriteGuest,
  deleteFavoriteUser,
  getRecommendations,
  listFavoritesGuest,
  listFavoritesUser,
  reverseGeocode,
  starFavoriteGuest,
  starFavoriteUser,
} from "../lib/api";
import { clearOriginState, loadOriginState, saveOriginState } from "../lib/originStorage";
import type {
  MealFilter,
  OriginMode,
  Recommendation,
  RecommendationRequest,
  TravelMode,
} from "../types/api";

interface SearchSummary {
  origin: string;
  meal: MealFilter;
  day: string | null;
}

const MEAL_OPTIONS: MealFilter[] = ["Breakfast", "Lunch", "Dinner"];

const HOURS_FALLBACK_BY_VENUE_ID: Record<string, string> = {
  segundo: "https://housing.ucdavis.edu/dining/dining-commons/segundo/",
  tercero: "https://housing.ucdavis.edu/dining/dining-commons/tercero/",
  cuarto: "https://housing.ucdavis.edu/dining/dining-commons/cuarto/",
  latitude: "https://housing.ucdavis.edu/dining/dining-commons/latitude/",
};

function normalizeItemName(itemName: string): string {
  return itemName.trim().toLowerCase().replace(/\s+/g, " ");
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill={filled ? "#DAAA00" : "none"}
      stroke={filled ? "#DAAA00" : "#5C6E7E"}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3.8L14.58 9.03L20.35 9.87L16.18 13.93L17.16 19.67L12 16.96L6.84 19.67L7.82 13.93L3.65 9.87L9.42 9.03L12 3.8Z" />
    </svg>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { selectedDay, dayOverride, setSelectedDay } = useDemoDay();
  const savedOrigin = loadOriginState();

  const [originMode, setOriginMode] = useState<OriginMode | null>(savedOrigin?.origin_mode ?? null);
  const [originLatitude, setOriginLatitude] = useState<number | null>(savedOrigin?.origin_latitude ?? null);
  const [originLongitude, setOriginLongitude] = useState<number | null>(
    savedOrigin?.origin_longitude ?? null,
  );
  const [originText, setOriginText] = useState(savedOrigin?.origin_text ?? "");
  const [originResolved, setOriginResolved] = useState(savedOrigin?.origin_resolved ?? "");
  const [typedAddressInput, setTypedAddressInput] = useState(savedOrigin?.origin_text ?? "");
  const [locationStatus, setLocationStatus] = useState("Current location not set yet.");
  const [locationError, setLocationError] = useState<string | null>(null);

  const [mealFilter, setMealFilter] = useState<MealFilter>("Lunch");
  const [keyword, setKeyword] = useState("");
  const [travelMode, setTravelMode] = useState<TravelMode>("walking");

  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [recommendationMessage, setRecommendationMessage] = useState<string | null>(null);
  const [summary, setSummary] = useState<SearchSummary | null>(null);

  const [favoriteMap, setFavoriteMap] = useState<Record<string, number>>({});
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const isLocationConfirmed = useMemo(() => {
    return Boolean(originMode && originResolved);
  }, [originMode, originResolved]);

  const isResultsPhase = useMemo(() => {
    return loadingRecommendations || recommendations.length > 0 || Boolean(recommendationMessage);
  }, [loadingRecommendations, recommendations.length, recommendationMessage]);

  async function refreshFavorites() {
    setFavoritesLoading(true);
    try {
      const response = user ? await listFavoritesUser() : await listFavoritesGuest();
      const nextMap: Record<string, number> = {};
      for (const favorite of response.favorites) {
        nextMap[normalizeItemName(favorite.item_name)] = favorite.id;
      }
      setFavoriteMap(nextMap);
    } catch {
      // Keep page usable even if favorites request fails.
    } finally {
      setFavoritesLoading(false);
    }
  }

  useEffect(() => {
    void refreshFavorites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  function resetLocation() {
    setOriginMode(null);
    setOriginLatitude(null);
    setOriginLongitude(null);
    setOriginText("");
    setOriginResolved("");
    setTypedAddressInput("");
    setLocationError(null);
    setLocationStatus("Location reset.");
    clearOriginState();
  }

  async function handleUseCurrentLocation() {
    setLocationError(null);
    setLocationStatus("Requesting current location...");

    if (!navigator.geolocation) {
      setLocationError("Geolocation is not supported in this browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        void (async () => {
          let resolvedAddress = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
          try {
            const geocodeResult = await reverseGeocode(latitude, longitude);
            if (geocodeResult.formatted_address) {
              resolvedAddress = geocodeResult.formatted_address;
            }
          } catch {
            // Keep fallback coordinate string if reverse geocoding fails.
          }

          setOriginMode("current");
          setOriginLatitude(latitude);
          setOriginLongitude(longitude);
          setOriginText("");
          setOriginResolved(resolvedAddress);
          setLocationStatus(`Current location set: ${resolvedAddress}`);

          saveOriginState({
            origin_mode: "current",
            origin_resolved: resolvedAddress,
            origin_latitude: latitude,
            origin_longitude: longitude,
          });
        })();
      },
      (error) => {
        setLocationError(`Location unavailable: ${error.message}`);
        setLocationStatus("Try typing your address below.");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    );
  }

  function handleConfirmTypedLocation() {
    const normalized = typedAddressInput.trim();
    if (!normalized) {
      setLocationError("Please type an address first.");
      return;
    }
    setLocationError(null);
    setOriginMode("typed");
    setOriginLatitude(null);
    setOriginLongitude(null);
    setOriginText(normalized);
    setOriginResolved(normalized);
    setLocationStatus(`Typed location set: ${normalized}`);

    saveOriginState({
      origin_mode: "typed",
      origin_resolved: normalized,
      origin_text: normalized,
    });
  }

  async function handleFindFood() {
    if (!isLocationConfirmed || !originMode) {
      setRecommendationError("Set your location before searching.");
      return;
    }

    setRecommendationError(null);
    setRecommendationMessage(null);
    setLoadingRecommendations(true);
    setRecommendations([]);
    setActionMessage(null);

    const requestPayload: RecommendationRequest = {
      keyword: keyword.trim(),
      meal_filter: mealFilter,
      travel_mode: travelMode,
      max_results: 5,
      sort_mode: "closest",
      result_mode: "global",
      per_hall_limit: 5,
      origin_mode: originMode,
    };
    if (dayOverride) {
      requestPayload.day_override = dayOverride;
    }

    if (originMode === "current") {
      if (originLatitude === null || originLongitude === null) {
        setLoadingRecommendations(false);
        setRecommendationError("Current coordinates are missing. Re-set your location.");
        return;
      }
      requestPayload.origin_latitude = originLatitude;
      requestPayload.origin_longitude = originLongitude;
    } else {
      requestPayload.origin_text = originText;
    }

    try {
      const response = await getRecommendations(requestPayload);
      setRecommendations(response.recommendations);
      setRecommendationMessage(response.recommendations.length === 0 ? response.message ?? null : null);
      setSummary({
        origin: response.origin_resolved ?? originResolved,
        meal: response.applied_meal ?? mealFilter,
        day: response.applied_day ?? null,
      });
    } catch (error) {
      if (error instanceof ApiError) {
        setRecommendationError(error.detail);
      } else {
        setRecommendationError("Unable to load recommendations.");
      }
    } finally {
      setLoadingRecommendations(false);
    }
  }

  async function handleToggleFavorite(itemName: string) {
    const normalized = normalizeItemName(itemName);
    const existingFavoriteId = favoriteMap[normalized];
    setActionMessage(existingFavoriteId ? "Removing favorite..." : "Saving favorite...");
    try {
      if (existingFavoriteId) {
        if (user) {
          await deleteFavoriteUser(existingFavoriteId);
        } else {
          await deleteFavoriteGuest(existingFavoriteId);
        }
      } else if (user) {
        await starFavoriteUser(itemName);
      } else {
        await starFavoriteGuest(itemName);
      }
      await refreshFavorites();
      setActionMessage(existingFavoriteId ? `Removed "${itemName}" from favorites.` : `Saved "${itemName}" to favorites.`);
    } catch (error) {
      if (error instanceof ApiError) {
        setActionMessage(error.detail);
      } else {
        setActionMessage("Unable to update favorite.");
      }
    }
  }

  function openRoutePage(recommendation: Recommendation) {
    const destinationText = `${recommendation.venue_name}, Davis, CA`;
    navigate(
      `/route?destination=${encodeURIComponent(destinationText)}&travel_mode=${encodeURIComponent(travelMode)}`,
    );
  }

  function getHoursUrl(recommendation: Recommendation): string | null {
    return (
      recommendation.hours_url ??
      HOURS_FALLBACK_BY_VENUE_ID[recommendation.venue_id] ??
      null
    );
  }

  return (
    <div className="space-y-8">
      <section className="flex justify-end">
        <DemoDayFilter selectedDay={selectedDay} onChange={setSelectedDay} />
      </section>

      <section className="rounded-card border border-border-default bg-surface-white p-6 md:p-10">
        <h1 className="text-2xl font-semibold tracking-[-0.01em] text-ink-primary">Where are you?</h1>
        <p className="mt-2 text-sm text-ink-3">Set your starting point to find nearby options.</p>

        <div className="mt-8">
          <button
            type="button"
            onClick={() => void handleUseCurrentLocation()}
            className="h-[52px] w-full rounded-input border border-border-default bg-surface-page px-4 text-left text-[15px] font-medium text-ink-primary transition hover:border-brand-blue"
          >
            Use my current location
          </button>
          <p className="mt-2 text-sm text-ink-3">{locationStatus}</p>
          {locationError ? (
            <p className="mt-3 rounded-pill bg-status-error-bg px-3 py-2 text-xs text-status-error-text">
              {locationError}
            </p>
          ) : null}
        </div>

        <div className="my-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-border-default" />
          <span className="text-xs text-ink-4">or type an address</span>
          <div className="h-px flex-1 bg-border-default" />
        </div>

        <div className="flex flex-col gap-3 md:flex-row">
          <input
            value={typedAddressInput}
            onChange={(event) => setTypedAddressInput(event.target.value)}
            placeholder="1 Shields Ave, Davis, CA"
            className="h-[52px] w-full rounded-input border border-border-default px-4 text-[15px] text-ink-primary outline-none transition focus:border-2 focus:border-brand-blue"
          />
          <button
            type="button"
            onClick={handleConfirmTypedLocation}
            className="h-[52px] rounded-button bg-brand-blue px-6 text-sm font-medium text-white transition hover:bg-brand-blue-mid"
          >
            Confirm
          </button>
        </div>

        {isLocationConfirmed ? (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-pill border border-brand-gold bg-brand-gold-tint px-4 py-2">
            <span className="mono-value text-sm text-brand-gold-dim">Location: {originResolved}</span>
            <button
              type="button"
              onClick={resetLocation}
              className="text-sm text-ink-3 underline-offset-4 transition hover:underline"
            >
              Reset
            </button>
          </div>
        ) : null}
      </section>

      {isLocationConfirmed ? (
        <section
          className={`rounded-card border border-border-default bg-surface-white p-6 md:p-10 ${
            isResultsPhase ? "opacity-70 transition-opacity duration-300" : ""
          }`}
        >
          <h2 className="text-[18px] font-medium text-ink-primary">Select your meal.</h2>
          <p className="mt-2 text-sm text-ink-3">We will show top protein options for that meal.</p>

          <div className="mt-6">
            <p className="text-[12px] font-semibold uppercase tracking-[0.07em] text-ink-3">Meal filter</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {MEAL_OPTIONS.map((meal) => (
                <button
                  key={meal}
                  type="button"
                  onClick={() => setMealFilter(meal)}
                  className={`rounded-pill px-5 py-2 text-sm transition ${
                    mealFilter === meal
                      ? "border border-brand-blue bg-brand-blue text-white"
                      : "border border-border-default bg-white text-ink-2 hover:border-brand-blue"
                  }`}
                >
                  {meal}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6">
            <label className="text-[12px] font-semibold uppercase tracking-[0.07em] text-ink-3">
              Keyword (optional)
            </label>
            <p className="mt-2 text-xs text-ink-4">e.g. smoothie, bowl, burrito, chicken</p>
            <input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="What are you looking for?"
              className="mt-2 h-12 w-full rounded-input border border-border-default px-4 text-[15px] text-ink-primary outline-none transition focus:border-2 focus:border-brand-blue"
            />
          </div>

          <div className="mt-6">
            <label className="text-[12px] font-semibold uppercase tracking-[0.07em] text-ink-3">
              Travel mode
            </label>
            <div className="mt-2 flex gap-2">
              {(["walking", "driving"] as TravelMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setTravelMode(mode)}
                  className={`rounded-pill px-4 py-2 text-sm ${
                    travelMode === mode
                      ? "bg-brand-blue text-white"
                      : "border border-border-default bg-white text-ink-2 hover:border-brand-blue"
                  }`}
                >
                  {mode === "walking" ? "Walking" : "Driving"}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={() => void handleFindFood()}
            disabled={loadingRecommendations || !isLocationConfirmed}
            className="mt-8 h-[52px] w-full rounded-button bg-brand-blue text-[15px] font-medium text-white transition hover:bg-brand-blue-mid disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loadingRecommendations ? "Finding options..." : "Find food"}
          </button>

          {recommendationError ? (
            <p className="mt-4 rounded-input border border-status-error-text bg-status-error-bg px-3 py-2 text-sm text-status-error-text">
              {recommendationError}
            </p>
          ) : null}
        </section>
      ) : null}

      {summary ? (
        <section className="rounded-input border border-border-default bg-surface-page px-4 py-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="mono-value text-brand-blue">Location: {summary.origin}</span>
            <span className="text-ink-4">|</span>
            <span className="mono-value text-brand-blue">{summary.meal}</span>
            {summary.day ? (
              <>
                <span className="text-ink-4">|</span>
                <span className="mono-value text-brand-blue">{summary.day}</span>
              </>
            ) : null}
            <button
              type="button"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="ml-auto text-brand-blue underline-offset-4 transition hover:underline"
            >
              Edit search {"<-"}
            </button>
          </div>
        </section>
      ) : null}

      {(loadingRecommendations || recommendations.length > 0 || recommendationMessage) && (
        <section>
          <h2 className="text-[18px] font-medium text-ink-primary">Nearby options</h2>
          <p className="mt-1 text-sm text-ink-4">Sorted by distance, then protein</p>

          {loadingRecommendations ? (
            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="rounded-card border border-border-default bg-surface-white p-5">
                  <div className="h-4 w-28 rounded-input border border-border-default bg-surface-page" />
                  <div className="mt-3 h-3 w-20 rounded-input border border-border-default bg-surface-page" />
                  <div className="mt-6 h-4 w-24 rounded-input border border-border-default bg-surface-page" />
                </div>
              ))}
            </div>
          ) : null}

          {!loadingRecommendations && recommendationMessage ? (
            <div className="mt-5 rounded-card border border-border-default bg-surface-white p-6 text-center">
              <p className="text-[15px] text-ink-2">Nothing nearby matches your goal.</p>
              <p className="mt-2 text-sm text-ink-3">
                Try another keyword or a different meal filter.
              </p>
            </div>
          ) : null}

          {!loadingRecommendations && recommendations.length > 0 ? (
            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              {recommendations.map((recommendation, index) => {
                const normalized = normalizeItemName(recommendation.item_name);
                const isStarred = Boolean(favoriteMap[normalized]);
                const hoursUrl = getHoursUrl(recommendation);
                return (
                  <article
                    key={`${recommendation.venue_id}-${recommendation.item_name}-${index}`}
                    className={`rounded-card border bg-surface-white p-5 transition hover:border-brand-blue ${
                      index === 0
                        ? "border-border-default border-l-[3px] border-l-brand-gold"
                        : "border-border-default"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        {index === 0 ? (
                          <span className="inline-flex rounded-pill bg-brand-gold-tint px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.04em] text-brand-gold-dim">
                            Best match
                          </span>
                        ) : null}
                        <h3 className="mt-3 text-base font-semibold text-ink-primary">
                          {recommendation.venue_name}
                        </h3>
                        <p className="mono-value mt-1 text-[13px] text-ink-3">
                          {recommendation.distance_miles ?? "N/A"} mi | {recommendation.duration ?? "N/A"}{" "}
                          {travelMode}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => void handleToggleFavorite(recommendation.item_name)}
                        disabled={favoritesLoading}
                        title={isStarred ? "Remove favorite" : "Add favorite"}
                        className={`rounded-pill border p-2 transition disabled:cursor-not-allowed disabled:opacity-50 ${
                          isStarred
                            ? "border-brand-gold bg-brand-gold-tint shadow-[0_0_0_2px_rgba(218,170,0,0.25)]"
                            : "border-border-default bg-surface-white hover:border-brand-gold"
                        }`}
                      >
                        <StarIcon filled={isStarred} />
                      </button>
                    </div>

                    <div className="mt-4 border-t border-border-default pt-3">
                      <p className="text-sm font-medium text-ink-2">{recommendation.item_name}</p>
                      <div className="mt-2 inline-flex rounded-pill bg-brand-gold-tint px-3 py-1">
                        <span className="mono-value text-[13px] font-medium text-brand-gold-dim">
                          {recommendation.protein_grams}g protein
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-ink-4">
                        Calories:{" "}
                        {recommendation.calories === null || recommendation.calories === undefined
                          ? "N/A"
                          : recommendation.calories}
                      </p>
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-border-default pt-3">
                      {hoursUrl ? (
                        <a
                          href={hoursUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-brand-blue underline-offset-4 transition hover:underline"
                        >
                          View hours
                        </a>
                      ) : (
                        <span className="text-xs text-ink-4">View hours unavailable</span>
                      )}
                      <button
                        type="button"
                        onClick={() => openRoutePage(recommendation)}
                        className="text-sm text-brand-blue underline-offset-4 transition hover:underline"
                      >
                        View route {"->"}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </section>
      )}

      {actionMessage ? (
        <section className="rounded-input border border-status-info-text bg-status-info-bg px-4 py-3 text-sm text-status-info-text">
          {actionMessage}
        </section>
      ) : null}
    </div>
  );
}
