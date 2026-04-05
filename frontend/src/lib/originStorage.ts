import type { OriginMode } from "../types/api";

const ORIGIN_STORAGE_KEY = "dprotein_origin_state";

export interface StoredOriginState {
  origin_mode: OriginMode;
  origin_resolved: string;
  origin_latitude?: number;
  origin_longitude?: number;
  origin_text?: string;
}

export function saveOriginState(payload: StoredOriginState): void {
  sessionStorage.setItem(ORIGIN_STORAGE_KEY, JSON.stringify(payload));
}

export function loadOriginState(): StoredOriginState | null {
  const raw = sessionStorage.getItem(ORIGIN_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as StoredOriginState;
    if (!parsed.origin_mode || !parsed.origin_resolved) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function clearOriginState(): void {
  sessionStorage.removeItem(ORIGIN_STORAGE_KEY);
}
