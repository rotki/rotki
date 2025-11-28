export const KEY_BACKEND_URL = 'rotki.backend_url';

export const KEY_BACKEND_URL_SESSION_ONLY = 'rotki.backend_url_session';
const KEY_LAST_LOGIN = 'rotki.last_login';

export interface BackendSettings {
  readonly url: string;
  readonly sessionOnly: boolean;
}

export function deleteBackendUrl(): void {
  localStorage.removeItem(KEY_BACKEND_URL);
  localStorage.removeItem(KEY_BACKEND_URL_SESSION_ONLY);
}

export function saveBackendUrl({ sessionOnly, url }: BackendSettings): void {
  localStorage.setItem(KEY_BACKEND_URL, url);
  if (sessionOnly)
    localStorage.setItem(KEY_BACKEND_URL_SESSION_ONLY, `${true}`);
  else localStorage.removeItem(KEY_BACKEND_URL_SESSION_ONLY);
}

export function getBackendUrl(): BackendSettings {
  const sessionOnly = !!localStorage.getItem(KEY_BACKEND_URL_SESSION_ONLY) || false;
  const url = localStorage.getItem(KEY_BACKEND_URL) ?? '';
  return {
    sessionOnly,
    url,
  };
}

export const lastLogin = useLocalStorage<string>(KEY_LAST_LOGIN, '');
