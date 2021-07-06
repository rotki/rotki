import { BackendCode } from '@/electron-main/backend-code';
import { Level } from '@/utils/log-level';

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
  readonly logDirectory: string;
  readonly sleepSeconds: number;
  readonly logFromOtherModules: boolean;
  readonly maxSizeInMbAllLogs: number;
  readonly maxLogfilesNum: number;
};

export type TrayUpdate = {
  readonly percentage?: string;
  readonly delta?: string;
  readonly netWorth?: string;
  readonly up?: boolean;
  readonly currency?: string;
  readonly period?: string;
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
  websocketUrl(): string;
  metamaskImport(): Promise<MetamaskImport>;
  checkForUpdates(): Promise<boolean>;
  downloadUpdate(progress: (percentage: number) => void): Promise<boolean>;
  installUpdate(): Promise<boolean | Error>;
  restartBackend(options: Partial<BackendOptions>): Promise<boolean>;
  setDarkMode(enabled: boolean): Promise<boolean>;
  version(): Promise<SystemVersion>;
  onAbout(callback: () => void): void;
  config(defaults: boolean): Promise<Partial<BackendOptions>>;
  updateTray(trayUpdate: TrayUpdate): Promise<void>;
}
