const GUEST_MODE_STORAGE_KEY = "dprotein_guest_mode";

export function enableGuestMode(): void {
  sessionStorage.setItem(GUEST_MODE_STORAGE_KEY, "1");
}

export function clearGuestMode(): void {
  sessionStorage.removeItem(GUEST_MODE_STORAGE_KEY);
}

export function isGuestModeEnabled(): boolean {
  return sessionStorage.getItem(GUEST_MODE_STORAGE_KEY) === "1";
}
