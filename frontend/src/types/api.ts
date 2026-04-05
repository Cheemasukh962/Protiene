export type OriginMode = "current" | "typed";
export type TravelMode = "walking" | "driving";
export type SortMode = "protein" | "closest";
export type ResultMode = "global" | "per_hall";
export type MealFilter = "Breakfast" | "Lunch" | "Dinner";
export type WeekdayName =
  | "Monday"
  | "Tuesday"
  | "Wednesday"
  | "Thursday"
  | "Friday"
  | "Saturday"
  | "Sunday";
export type DemoDaySelection = "Today" | WeekdayName;

export interface AuthUser {
  id: number;
  email: string;
  is_active: boolean;
}

export interface RegisterResponse {
  id: number;
  email: string;
  created_at: string;
}

export interface LoginResponse {
  ok: boolean;
  email: string;
}

export interface Recommendation {
  venue_id: string;
  venue_name: string;
  venue_category: string;
  item_name: string;
  protein_grams: number;
  calories?: number | null;
  tags: string[];
  distance_miles?: number | null;
  duration?: string | null;
  hours_url?: string | null;
  why_selected: string;
  route_error?: string | null;
}

export interface PerHallRecommendationGroup {
  venue_name: string;
  items: Recommendation[];
}

export interface RecommendationRequest {
  origin_mode?: OriginMode;
  origin_latitude?: number;
  origin_longitude?: number;
  origin_text?: string;
  meal_filter?: MealFilter;
  day_override?: WeekdayName;
  keyword: string;
  travel_mode: TravelMode;
  max_results: number;
  sort_mode: SortMode;
  result_mode: ResultMode;
  per_hall_limit: number;
}

export interface RecommendationResponse {
  origin_resolved?: string | null;
  keyword: string;
  travel_mode: TravelMode;
  sort_mode: SortMode;
  result_mode: ResultMode;
  applied_day?: string | null;
  applied_meal?: MealFilter | null;
  recommendations: Recommendation[];
  per_hall_recommendations: PerHallRecommendationGroup[];
  message?: string;
}

export interface ReverseGeocodeResponse {
  formatted_address: string | null;
  place_id: string | null;
  status?: string;
  error?: string;
}

export interface RouteStep {
  step_number: number;
  instruction_text: string;
  distance_miles: number;
  duration_seconds?: number | null;
  duration_text?: string | null;
}

export interface RouteRequest {
  origin_mode: OriginMode;
  origin_latitude?: number;
  origin_longitude?: number;
  origin_text?: string;
  destination_text: string;
  travel_mode: TravelMode;
}

export interface RouteResponse {
  origin_mode: OriginMode;
  origin_resolved: string;
  destination_resolved: string;
  travel_mode: string;
  distance_miles?: number | null;
  duration?: string | null;
  encoded_polyline?: string | null;
  steps: RouteStep[];
  route_error?: string | null;
}

export interface PublicMapConfigResponse {
  google_maps_js_api_key: string;
}

export interface FavoriteItem {
  id: number;
  item_name: string;
  created_at: string;
}

export interface FavoritesListResponse {
  favorites: FavoriteItem[];
}

export interface FavoriteStarResponse {
  ok: boolean;
  favorite: FavoriteItem;
}

export interface DeleteFavoriteResponse {
  ok: boolean;
}

export interface TrackerAvailableNowMatch {
  dining_hall: string;
  item_name: string;
  protein_grams: number;
  calories?: number | null;
  day_of_week: string;
  meal: string;
}

export interface TrackerAvailableNowResponse {
  applied_day: string;
  applied_meal: string | null;
  matches: TrackerAvailableNowMatch[];
}

export interface TrackerScheduleItem {
  item_name: string;
  dining_hall: string;
  day_of_week: string;
  meal: string;
  protein_grams: number;
  calories?: number | null;
}

export interface TrackerScheduleResponse {
  schedule: TrackerScheduleItem[];
}

export interface TrackerOverviewSlot {
  item_name: string;
  dining_hall: string;
  day_of_week: string;
  meal: string;
  protein_grams: number;
  calories?: number | null;
}

export interface TrackerOverviewFavorite {
  favorite_id: number;
  item_name: string;
  available_today: boolean;
  today_slots: TrackerOverviewSlot[];
  schedule: TrackerOverviewSlot[];
}

export interface TrackerOverviewResponse {
  applied_day: string;
  favorites: TrackerOverviewFavorite[];
}
