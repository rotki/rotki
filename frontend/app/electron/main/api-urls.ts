import type { ApiUrls } from '@shared/ipc';

export const apiUrls: ApiUrls = {
  coreApiUrl: import.meta.env.VITE_BACKEND_URL as string,
  colibriApiUrl: import.meta.env.VITE_COLIBRI_URL as string,
};
