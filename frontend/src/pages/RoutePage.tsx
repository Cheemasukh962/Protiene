import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ApiError, getPublicMapConfig, getRoute } from "../lib/api";
import { loadOriginState } from "../lib/originStorage";
import type { RouteResponse, TravelMode } from "../types/api";

declare global {
  interface Window {
    google?: {
      maps: {
        Map: new (element: HTMLElement, options: Record<string, unknown>) => GoogleMap;
        Polyline: new (options: Record<string, unknown>) => GooglePolyline;
        Marker: new (options: Record<string, unknown>) => GoogleMarker;
        LatLngBounds: new () => GoogleLatLngBounds;
        geometry: {
          encoding: {
            decodePath: (encoded: string) => GoogleLatLng[];
          };
        };
      };
    };
  }
}

interface GoogleMap {
  fitBounds: (bounds: GoogleLatLngBounds) => void;
}

interface GooglePolyline {
  setMap: (map: GoogleMap | null) => void;
  getPath: () => GoogleLatLng[];
}

interface GoogleMarker {
  setMap: (map: GoogleMap | null) => void;
}

interface GoogleLatLngBounds {
  extend: (point: GoogleLatLng) => void;
}

interface GoogleLatLng {
  lat: () => number;
  lng: () => number;
}

async function loadGoogleMapsSdk(apiKey: string): Promise<void> {
  if (window.google?.maps?.geometry) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const existing = document.getElementById("google-maps-sdk");
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Failed to load Google Maps SDK.")), {
        once: true,
      });
      return;
    }

    const script = document.createElement("script");
    script.id = "google-maps-sdk";
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=geometry`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Maps SDK."));
    document.head.appendChild(script);
  });
}

export default function RoutePage() {
  const [searchParams] = useSearchParams();
  const storedOrigin = loadOriginState();
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<GoogleMap | null>(null);
  const polylineRef = useRef<GooglePolyline | null>(null);
  const markersRef = useRef<GoogleMarker[]>([]);

  const [destinationText, setDestinationText] = useState(searchParams.get("destination") ?? "");
  const [travelMode, setTravelMode] = useState<TravelMode>(
    (searchParams.get("travel_mode") as TravelMode) ?? "walking",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [routeResult, setRouteResult] = useState<RouteResponse | null>(null);
  const [mapStatus, setMapStatus] = useState("Loading map...");

  const canSubmit = useMemo(() => {
    return Boolean(storedOrigin && destinationText.trim().length > 0 && !loading);
  }, [storedOrigin, destinationText, loading]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const config = await getPublicMapConfig();
        if (!config.google_maps_js_api_key) {
          throw new Error("Google Maps key is missing.");
        }
        await loadGoogleMapsSdk(config.google_maps_js_api_key);
        if (!mounted || !mapContainerRef.current || !window.google?.maps) {
          return;
        }
        mapRef.current = new window.google.maps.Map(mapContainerRef.current, {
          center: { lat: 38.54, lng: -121.75 },
          zoom: 14,
          mapTypeControl: false,
        });
        setMapStatus("Map ready.");
      } catch (err) {
        if (!mounted) {
          return;
        }
        if (err instanceof Error) {
          setMapStatus(`Map unavailable: ${err.message}`);
        } else {
          setMapStatus("Map unavailable.");
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  function clearRenderedRoute() {
    if (polylineRef.current) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
    }
    for (const marker of markersRef.current) {
      marker.setMap(null);
    }
    markersRef.current = [];
  }

  function drawRoutePolyline(encodedPolyline: string) {
    if (!mapRef.current || !window.google?.maps?.geometry) {
      return;
    }
    const path = window.google.maps.geometry.encoding.decodePath(encodedPolyline);
    if (!path || path.length === 0) {
      return;
    }

    clearRenderedRoute();

    polylineRef.current = new window.google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor: "#1A3F6B",
      strokeOpacity: 0.95,
      strokeWeight: 5,
      map: mapRef.current,
    });

    const originMarker = new window.google.maps.Marker({
      map: mapRef.current,
      position: path[0],
      title: "Origin",
    });
    const destinationMarker = new window.google.maps.Marker({
      map: mapRef.current,
      position: path[path.length - 1],
      title: "Destination",
    });
    markersRef.current = [originMarker, destinationMarker];

    const bounds = new window.google.maps.LatLngBounds();
    for (const point of path) {
      bounds.extend(point);
    }
    mapRef.current.fitBounds(bounds);
  }

  useEffect(() => {
    if (!routeResult?.encoded_polyline) {
      return;
    }
    drawRoutePolyline(routeResult.encoded_polyline);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeResult?.encoded_polyline, mapStatus]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!storedOrigin) {
      return;
    }

    setError(null);
    setLoading(true);
    setRouteResult(null);

    try {
      const payload =
        storedOrigin.origin_mode === "current"
          ? {
              origin_mode: "current" as const,
              origin_latitude: storedOrigin.origin_latitude,
              origin_longitude: storedOrigin.origin_longitude,
              destination_text: destinationText.trim(),
              travel_mode: travelMode,
            }
          : {
              origin_mode: "typed" as const,
              origin_text: storedOrigin.origin_text ?? storedOrigin.origin_resolved,
              destination_text: destinationText.trim(),
              travel_mode: travelMode,
            };

      const response = await getRoute(payload);
      setRouteResult(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Unable to load route.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (!storedOrigin) {
    return (
      <section className="rounded-card border border-border-default bg-surface-white p-6 md:p-10">
        <h1 className="text-2xl font-semibold text-ink-primary">Route view</h1>
        <p className="mt-3 text-sm text-ink-3">
          No origin found in this browser session. Set your location on home first.
        </p>
        <Link to="/" className="mt-4 inline-block text-brand-blue underline-offset-4 hover:underline">
          Back to home
        </Link>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-border-default bg-surface-white p-6 md:p-10">
        <h1 className="text-2xl font-semibold text-ink-primary">Route details</h1>
        <p className="mt-2 text-sm text-ink-3">
          Origin: <span className="mono-value text-brand-blue">{storedOrigin.origin_resolved}</span>
        </p>

        <form onSubmit={(event) => void handleSubmit(event)} className="mt-6 space-y-4">
          <div>
            <label className="text-[12px] font-semibold uppercase tracking-[0.07em] text-ink-3">
              Destination
            </label>
            <input
              value={destinationText}
              onChange={(event) => setDestinationText(event.target.value)}
              placeholder="Segundo Dining Commons, Davis CA"
              className="mt-2 h-12 w-full rounded-input border border-border-default px-4 text-[15px] text-ink-primary outline-none transition focus:border-2 focus:border-brand-blue"
            />
          </div>

          <div>
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
            type="submit"
            disabled={!canSubmit}
            className="h-12 rounded-button bg-brand-blue px-6 text-sm font-medium text-white transition hover:bg-brand-blue-mid disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Loading route..." : "View route"}
          </button>
        </form>

        {error ? (
          <p className="mt-4 rounded-input border border-status-error-text bg-status-error-bg px-3 py-2 text-sm text-status-error-text">
            {error}
          </p>
        ) : null}
      </section>

      <section className="rounded-card border border-border-default bg-surface-white p-6 md:p-10">
        <h2 className="text-[18px] font-medium text-ink-primary">Map</h2>
        <p className="mt-2 text-sm text-ink-3">{mapStatus}</p>
        <div
          ref={mapContainerRef}
          className="mt-4 h-[430px] w-full rounded-card border border-border-default bg-surface-page"
        />
      </section>

      {routeResult ? (
        <section className="rounded-card border border-border-default bg-surface-white p-6 md:p-10">
          <h2 className="text-[18px] font-medium text-ink-primary">Route summary</h2>
          <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <p>
              Destination:{" "}
              <span className="mono-value text-ink-2">{routeResult.destination_resolved}</span>
            </p>
            <p>
              Distance:{" "}
              <span className="mono-value text-ink-2">{routeResult.distance_miles ?? "N/A"} mi</span>
            </p>
            <p>
              Duration: <span className="mono-value text-ink-2">{routeResult.duration ?? "N/A"}</span>
            </p>
            <p>
              Mode: <span className="mono-value text-ink-2">{routeResult.travel_mode}</span>
            </p>
          </div>

          <div className="mt-6">
            <h3 className="text-sm font-semibold uppercase tracking-[0.07em] text-ink-3">
              Turn-by-turn steps
            </h3>
            {routeResult.steps.length === 0 ? (
              <p className="mt-2 text-sm text-ink-3">No steps returned.</p>
            ) : (
              <ol className="mt-3 space-y-2">
                {routeResult.steps.map((step) => (
                  <li
                    key={step.step_number}
                    className="rounded-input border border-border-default bg-surface-page px-3 py-2 text-sm text-ink-2"
                  >
                    <p>
                      <span className="mono-value mr-2 text-ink-3">{step.step_number}.</span>
                      {step.instruction_text}
                    </p>
                    <p className="mt-1 text-xs text-ink-4">
                      {step.distance_miles} mi | {step.duration_text ?? "N/A"}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
