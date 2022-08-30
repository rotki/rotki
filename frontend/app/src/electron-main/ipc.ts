import { DebugSettings } from '@rotki/common/lib/settings';
import { z } from 'zod';
import { BackendCode } from '@/electron-main/backend-code';
import { LogLevel } from '@/utils/log-level';

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

export const ActiveLogLevel = z.preprocess(
  s => (typeof s === 'string' ? s.toLowerCase() : s),
  z.nativeEnum(LogLevel)
);

export const BackendOptions = z.object({
  loglevel: ActiveLogLevel.optional(),
  dataDirectory: z.string().optional(),
  logDirectory: z.string().optional(),
  sleepSeconds: z.number().nonnegative().optional(),
  logFromOtherModules: z.boolean().optional(),
  maxSizeInMbAllLogs: z.number().optional(),
  sqliteInstructions: z.number().optional(),
  maxLogfilesNum: z.number().optional()
});

export type StoredBackendOptions = z.infer<typeof BackendOptions>;

export type BackendOptions = Required<StoredBackendOptions>;

export type TrayUpdate = {
  readonly percentage?: string;
  readonly delta?: string;
  readonly netWorth?: string;
  readonly up?: boolean;
  readonly currency?: string;
  readonly period?: string;
};

export interface Listeners {
  onError(backendOutput: string, code: BackendCode): void;
  onAbout(): void;
  onRestart(): void;
  onProcessDetected(pids: string[]): void;
}

export interface Interop {
  openUrl(url: string): void;
  openPath(path: string): void;
  closeApp(): void;
  setListeners(listeners: Listeners): void;
  openDirectory(title: string): Promise<undefined | string>;
  premiumUserLoggedIn(premiumUser: boolean): void;
  monitorDebugSettings(): void;
  debugSettings?(): DebugSettings | undefined;
  serverUrl(): string;
  metamaskImport(): Promise<MetamaskImport>;
  checkForUpdates(): Promise<boolean>;
  downloadUpdate(progress: (percentage: number) => void): Promise<boolean>;
  installUpdate(): Promise<boolean | Error>;
  restartBackend(options: Partial<BackendOptions>): Promise<boolean>;
  setSelectedTheme(selectedTheme: number): Promise<boolean>;
  version(): Promise<SystemVersion>;
  isMac(): Promise<boolean>;
  config(defaults: boolean): Promise<Partial<BackendOptions>>;
  updateTray(trayUpdate: TrayUpdate): void;
  logToFile(message: string): void;
  storePassword(username: string, password: string): Promise<boolean>;
  getPassword(username: string): Promise<string>;
  clearPassword(): Promise<void>;
}
