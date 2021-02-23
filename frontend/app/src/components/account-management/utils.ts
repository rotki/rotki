export const KEY_BACKEND_URL = 'rotki.backend_url';
export const KEY_BACKEND_URL_SESSION_ONLY = 'rotki.backend_url_session';

export type BackendSettings = {
  readonly url: string;
  readonly sessionOnly: boolean;
};

export function deleteBackendUrl() {
  localStorage.removeItem(KEY_BACKEND_URL);
  localStorage.removeItem(KEY_BACKEND_URL_SESSION_ONLY);
}

export function saveBackendUrl({ sessionOnly, url }: BackendSettings) {
  localStorage.setItem(KEY_BACKEND_URL, url);
  if (sessionOnly) {
    localStorage.setItem(KEY_BACKEND_URL_SESSION_ONLY, `${true}`);
  } else {
    localStorage.removeItem(KEY_BACKEND_URL_SESSION_ONLY);
  }
}

export function getBackendUrl(): BackendSettings {
  const sessionOnly =
    !!localStorage.getItem(KEY_BACKEND_URL_SESSION_ONLY) ?? false;
  const url = localStorage.getItem(KEY_BACKEND_URL) ?? '';
  return {
    url,
    sessionOnly
  };
}
