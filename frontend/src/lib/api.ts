import type {
  AuthUser,
  DeleteFavoriteResponse,
  FavoriteStarResponse,
  FavoritesListResponse,
  LoginResponse,
  PublicMapConfigResponse,
  RecommendationRequest,
  RecommendationResponse,
  RegisterResponse,
  ReverseGeocodeResponse,
  RouteRequest,
  RouteResponse,
  TrackerAvailableNowResponse,
  TrackerOverviewResponse,
  TrackerScheduleResponse,
  WeekdayName,
} from "../types/api";

const DEFAULT_API_BASE_URL = `http://${window.location.hostname}:8000`;

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(
  /\/+$/,
  "",
);

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions extends RequestInit {
  bodyJson?: unknown;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  if (options.bodyJson !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers,
    body: options.bodyJson !== undefined ? JSON.stringify(options.bodyJson) : options.body,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = data?.detail ?? `Request failed (${response.status})`;
    throw new ApiError(response.status, detail);
  }

  return data as T;
}

export function registerUser(email: string, password: string): Promise<RegisterResponse> {
  return request("/auth/register", {
    method: "POST",
    bodyJson: { email, password },
  });
}

export function loginUser(email: string, password: string): Promise<LoginResponse> {
  return request("/auth/login", {
    method: "POST",
    bodyJson: { email, password },
  });
}

export function fetchMe(): Promise<AuthUser> {
  return request("/auth/me");
}

export function logoutUser(): Promise<{ ok: boolean }> {
  return request("/auth/logout", {
    method: "POST",
    bodyJson: {},
  });
}

export function reverseGeocode(latitude: number, longitude: number): Promise<ReverseGeocodeResponse> {
  return request("/api/location/reverse-geocode", {
    method: "POST",
    bodyJson: { latitude, longitude },
  });
}

export function getRecommendations(
  payload: RecommendationRequest,
): Promise<RecommendationResponse> {
  return request("/api/recommendations", {
    method: "POST",
    bodyJson: payload,
  });
}

export function getRoute(payload: RouteRequest): Promise<RouteResponse> {
  return request("/api/route", {
    method: "POST",
    bodyJson: payload,
  });
}

export function getPublicMapConfig(): Promise<PublicMapConfigResponse> {
  return request("/api/public-map-config");
}

export function starFavoriteGuest(itemName: string): Promise<FavoriteStarResponse> {
  return request("/api/favorites/star", {
    method: "POST",
    bodyJson: { item_name: itemName },
  });
}

export function listFavoritesGuest(): Promise<FavoritesListResponse> {
  return request("/api/favorites");
}

export function deleteFavoriteGuest(favoriteId: number): Promise<DeleteFavoriteResponse> {
  return request(`/api/favorites/${favoriteId}`, {
    method: "DELETE",
  });
}

export function starFavoriteUser(itemName: string): Promise<FavoriteStarResponse> {
  return request("/api/user/favorites/star", {
    method: "POST",
    bodyJson: { item_name: itemName },
  });
}

export function listFavoritesUser(): Promise<FavoritesListResponse> {
  return request("/api/user/favorites");
}

export function deleteFavoriteUser(favoriteId: number): Promise<DeleteFavoriteResponse> {
  return request(`/api/user/favorites/${favoriteId}`, {
    method: "DELETE",
  });
}

export function trackerAvailableNowGuest(): Promise<TrackerAvailableNowResponse> {
  return request("/api/tracker/available-now");
}

export function trackerScheduleGuest(): Promise<TrackerScheduleResponse> {
  return request("/api/tracker/schedule");
}

export function trackerOverviewGuest(dayOverride?: WeekdayName): Promise<TrackerOverviewResponse> {
  const query = dayOverride ? `?day_override=${encodeURIComponent(dayOverride)}` : "";
  return request(`/api/tracker/overview${query}`);
}

export function trackerAvailableNowUser(): Promise<TrackerAvailableNowResponse> {
  return request("/api/user/tracker/available-now");
}

export function trackerScheduleUser(): Promise<TrackerScheduleResponse> {
  return request("/api/user/tracker/schedule");
}

export function trackerOverviewUser(dayOverride?: WeekdayName): Promise<TrackerOverviewResponse> {
  const query = dayOverride ? `?day_override=${encodeURIComponent(dayOverride)}` : "";
  return request(`/api/user/tracker/overview${query}`);
}
