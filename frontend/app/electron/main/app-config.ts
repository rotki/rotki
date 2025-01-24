import type { ApiUrls } from '@shared/ipc';

export interface AppConfig {
  readonly isDev: boolean;
  readonly isMac: boolean;
  readonly urls: ApiUrls;
  readonly ports: {
    colibriPort: number;
    corePort: number;
  };
}
