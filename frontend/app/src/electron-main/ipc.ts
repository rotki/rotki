import { z } from 'zod';
import { LogLevel } from '@/utils/log-level';
import type { DebugSettings } from '@rotki/common/lib/settings';

export const BackendCode = {
  TERMINATED: 0,
  MACOS_VERSION: 1,
  WIN_VERSION: 2,
};

export type BackendCode = typeof BackendCode[keyof typeof BackendCode];

export const IpcCommands = {
  RESTART_BACKEND: 'RESTART_BACKEND',
  REQUEST_RESTART: 'REQUEST_RESTART',
  BACKEND_PROCESS_DETECTED: 'BACKEND_PROCESS_DETECTED',
  CHECK_FOR_UPDATES: 'CHECK_FOR_UPDATES',
  DOWNLOAD_UPDATE: 'DOWNLOAD_UPDATE',
  DOWNLOAD_PROGRESS: 'DOWNLOAD_PROGRESS',
  INSTALL_UPDATE: 'INSTALL_UPDATE',
  THEME: 'THEME',
  VERSION: 'VERSION',
  IS_MAC: 'IS_MAC',
  ABOUT: 'ABOUT',
  OPEN_PATH: 'OPEN_PATH',
  CONFIG: 'CONFIG',
  METAMASK_IMPORT: 'METAMASK_IMPORT',
  SERVER_URL: 'SERVER_URL',
  GET_DEBUG: 'GET_DEBUG',
  OPEN_URL: 'OPEN_URL',
  OPEN_DIRECTORY: 'OPEN_DIRECTORY',
  DEBUG_SETTINGS: 'DEBUG_SETTINGS',
  CLOSE_APP: 'CLOSE_APP',
  PREMIUM_LOGIN: 'PREMIUM_USER_LOGGED_IN',
  TRAY_UPDATE: 'TRAY_UPDATE',
  LOG_TO_FILE: 'LOG_TO_FILE',
  STORE_PASSWORD: 'STORE_PASSWORD',
  GET_PASSWORD: 'GET_PASSWORD',
  CLEAR_PASSWORD: 'CLEAR_PASSWORD',
} as const;

export type IpcCommands = typeof IpcCommands[keyof typeof IpcCommands];

interface MetamaskImportError {
  readonly error: string;
}

interface MetamaskImportSupport {
  readonly addresses: string[];
}

type MetamaskImport = MetamaskImportError | MetamaskImportSupport;

export interface SystemVersion {
  readonly electron: string;
  readonly osVersion: string;
  readonly os: string;
  readonly arch: string;
}

export const ActiveLogLevel = z.preprocess(
  s => (typeof s === 'string' ? s.toLowerCase() : s),
  z.nativeEnum(LogLevel),
);

export const BackendOptions = z.object({
  loglevel: ActiveLogLevel.optional(),
  dataDirectory: z.string().optional(),
  logDirectory: z.string().optional(),
  sleepSeconds: z.number().nonnegative().optional(),
  logFromOtherModules: z.boolean().optional(),
  maxSizeInMbAllLogs: z.number().optional(),
  sqliteInstructions: z.number().optional(),
  maxLogfilesNum: z.number().optional(),
});

export type StoredBackendOptions = z.infer<typeof BackendOptions>;

export type BackendOptions = Required<StoredBackendOptions>;

export interface TrayUpdate {
  readonly percentage?: string;
  readonly delta?: string;
  readonly netWorth?: string;
  readonly up?: boolean;
  readonly currency?: string;
  readonly period?: string;
}

export interface Listeners {
  onError: (backendOutput: string, code: BackendCode) => void;
  onAbout: () => void;
  onRestart: () => void;
  onProcessDetected: (pids: string[]) => void;
}

export interface Interop {
  openUrl: (url: string) => void;
  openPath: (path: string) => void;
  closeApp: () => void;
  setListeners: (listeners: Listeners) => void;
  openDirectory: (title: string) => Promise<undefined | string>;
  premiumUserLoggedIn: (premiumUser: boolean) => void;
  monitorDebugSettings: () => void;
  debugSettings?: () => DebugSettings | undefined;
  serverUrl: () => string;
  metamaskImport: () => Promise<MetamaskImport>;
  checkForUpdates: () => Promise<boolean>;
  downloadUpdate: (progress: (percentage: number) => void) => Promise<boolean>;
  installUpdate: () => Promise<boolean | Error>;
  restartBackend: (options: Partial<BackendOptions>) => Promise<boolean>;
  setSelectedTheme: (selectedTheme: number) => Promise<boolean>;
  version: () => Promise<SystemVersion>;
  isMac: () => Promise<boolean>;
  config: (defaults: boolean) => Promise<Partial<BackendOptions>>;
  updateTray: (trayUpdate: TrayUpdate) => void;
  logToFile: (message: string) => void;
  storePassword: (username: string, password: string) => Promise<boolean>;
  getPassword: (username: string) => Promise<string>;
  clearPassword: () => Promise<void>;
}
