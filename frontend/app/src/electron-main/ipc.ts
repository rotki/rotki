import { BackendCode } from '@/electron-main/backend-code';
import { Level } from '@/utils/log-level';

export const IPC_RESTART_BACKEND = 'RESTART_BACKEND' as const;
export const IPC_CHECK_FOR_UPDATES = 'CHECK_FOR_UPDATES' as const;
export const IPC_DOWNLOAD_UPDATE = 'DOWNLOAD_UPDATE' as const;
export const IPC_DOWNLOAD_PROGRESS = 'DOWNLOAD_PROGRESS' as const;
export const IPC_INSTALL_UPDATE = 'INSTALL_UPDATE' as const;

export type DebugSettings = { vuex: boolean };

type MetamaskImportError = {
  readonly error: string;
};

type MetamaskImportSupport = {
  readonly addresses: string[];
};

type MetamaskImport = MetamaskImportError | MetamaskImportSupport;

export interface Interop {
  openUrl(url: string): Promise<void>;
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
  restartBackend(logLevel: Level): Promise<boolean>;
}
