/**
 * The origin the app addresses when nothing has overridden it: core answers
 * `/api/1/*` under it, colibri `/colibri/*`. Electron replaces it over IPC once
 * starling's proxy port is known; the custom-backend flow replaces it with the
 * url the user typed.
 */
function getDefaultApiUrl(): string {
  if (import.meta.env.VITE_BACKEND_URL)
    return import.meta.env.VITE_BACKEND_URL;

  if (import.meta.env.VITE_PUBLIC_PATH) {
    const pathname = window.location.pathname;
    return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  }

  return '';
}

export const defaultApiUrl: string = getDefaultApiUrl();
