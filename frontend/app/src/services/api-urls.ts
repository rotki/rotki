import type { ApiUrls } from '@shared/ipc';

function getDefaultCoreUrl(): string {
  if (import.meta.env.VITE_BACKEND_URL)
    return import.meta.env.VITE_BACKEND_URL as string;

  if (import.meta.env.VITE_PUBLIC_PATH) {
    const pathname = window.location.pathname;
    return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  }

  return '';
}

function getDefaultColibriUrl(): string {
  if (import.meta.env.VITE_COLIBRI_URL)
    return import.meta.env.VITE_COLIBRI_URL as string;

  if (import.meta.env.VITE_PUBLIC_PATH) {
    const pathname = window.location.pathname;
    return `${pathname.endsWith('/') ? pathname.slice(0, -1) : pathname}/colibri`;
  }

  return '';
}

export const defaultApiUrls: Readonly<ApiUrls> = {
  colibriApiUrl: getDefaultColibriUrl(),
  coreApiUrl: getDefaultCoreUrl(),
};

export const apiUrls: ApiUrls = {
  colibriApiUrl: defaultApiUrls.colibriApiUrl,
  coreApiUrl: defaultApiUrls.coreApiUrl,
};
