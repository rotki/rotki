import { BackendCode } from '@/electron-main/backend-code';
import { Level } from '@/utils/log-level';

export const IPC_RESTART_BACKEND = 'RESTART_BACKEND' as const;
export const IPC_CHECK_FOR_UPDATES = 'CHECK_FOR_UPDATES' as const;
export const IPC_DOWNLOAD_UPDATE = 'DOWNLOAD_UPDATE' as const;
export const IPC_DOWNLOAD_PROGRESS = 'DOWNLOAD_PROGRESS' as const;
export const IPC_INSTALL_UPDATE = 'INSTALL_UPDATE' as const;
export const IPC_DARK_MODE = 'DARK_MODE' as const;
export const IPC_VERSION = 'VERSION' as const;
export const IPC_ABOUT = 'ABOUT' as const;
export const IPC_OPEN_PATH = 'OPEN_PATH' as const;

export type DebugSettings = { vuex: boolean };

type MetamaskImportError = {
  readonly error: string;
};

type MetamaskImportSupport = {
  readonly addresses: string[];
};

type MetamaskImport = MetamaskImportError | MetamaskImportSupport;

export type SystemVersion = {
  readonly electron: string;
  readonly osVersion: string;
  readonly os: string;
  readonly arch: string;
};

export type BackendOptions = {
  readonly loglevel: Level;
  readonly dataDirectory: string;
  readonly logFile: string;
  readonly sleepSeconds?: number;
  readonly logFromOtherModules?: boolean;
};

export interface Interop {
  openUrl(url: string): Promise<void>;
  openPath(path: string): Promise<void>;
  closeApp(): void;
  listenForErrors(
    callback: (backendOutput: string, code: BackendCode) => void
  ): void;
  openDirectory(title: string): Promise<undefined | string>;
  premiumUserLoggedIn(premiumUser: boolean): Promise<undefined | boolean>;
  monitorDebugSettings(): void;
  debugSettings?(): DebugSettings | undefined;
  serverUrl(): string;
  metamaskImport(): Promise<MetamaskImport>;
  checkForUpdates(): Promise<boolean>;
  downloadUpdate(progress: (percentage: number) => void): Promise<boolean>;
  installUpdate(): Promise<boolean | Error>;
  restartBackend(options: BackendOptions): Promise<boolean>;
  setDarkMode(enabled: boolean): Promise<boolean>;
  version(): Promise<SystemVersion>;
  onAbout(callback: () => void): void;
}
