import type { DebugSettings } from '@rotki/common';
import { LogLevel } from '@shared/log-level';
import * as z from 'zod/mini';

export const BackendCode = {
  TERMINATED: 0,
  MACOS_VERSION: 1,
  WIN_VERSION: 2,
};

export type BackendCode = typeof BackendCode[keyof typeof BackendCode];

export interface StartupError {
  message: string;
  code: BackendCode;
}

export const StarlingServiceStatus = {
  DEGRADED: 'Degraded',
  FAILED: 'Failed',
  IDLE: 'Idle',
  READY: 'Ready',
  RESTARTING: 'Restarting',
  SPAWNING: 'Spawning',
  STOPPED: 'Stopped',
  STOPPING: 'Stopping',
  UNAVAILABLE: 'Unavailable',
  WAITING_READY: 'WaitingReady',
} as const;

export type StarlingServiceStatus = typeof StarlingServiceStatus[keyof typeof StarlingServiceStatus];

export interface McpServerStatus {
  autoStart: boolean;
  endpoint: string;
  state: StarlingServiceStatus;
}

interface MetamaskImportError {
  readonly error: string;
}

interface MetamaskImportSupport {
  readonly addresses: string[];
}

type MetamaskImport = MetamaskImportError | MetamaskImportSupport;

export interface Credentials {
  readonly username: string;
  readonly password: string;
}

export interface SystemVersion {
  readonly electron: string;
  readonly osVersion: string;
  readonly os: string;
  readonly arch: string;
}

export const ActiveLogLevel = z.pipe(
  z.transform(s => (typeof s === 'string' ? s.toLowerCase() : s)),
  z.enum(LogLevel),
);

export const BackendOptions = z.object({
  loglevel: z.optional(ActiveLogLevel),
  dataDirectory: z.optional(z.string()),
  logDirectory: z.optional(z.string()),
  sleepSeconds: z.optional(z.number().check(z.nonnegative())),
  logFromOtherModules: z.optional(z.boolean()),
  maxSizeInMbAllLogs: z.optional(z.int().check(z.positive())),
  sqliteInstructions: z.optional(z.int().check(z.positive())),
  maxLogfilesNum: z.optional(z.int().check(z.positive())),
  mcpAutoStart: z.optional(z.boolean()),
});

type StoredBackendOptions = z.infer<typeof BackendOptions>;

export type BackendOptions = Required<StoredBackendOptions>;

export interface TrayUpdate {
  readonly percentage?: string;
  readonly delta?: string;
  readonly netWorth?: string;
  readonly up?: boolean;
  readonly currency?: string;
  readonly period?: string;
}

interface OAuthSuccess {
  readonly success: true;
  readonly service: string;
  readonly accessToken: string;
  readonly refreshToken?: string;
  readonly expiresIn?: number;
}

interface OAuthFailure {
  readonly success: false;
  readonly service?: string;
  readonly error: Error;
}

export type OAuthResult = OAuthFailure | OAuthSuccess;

export interface WalletBridgeRequest {
  readonly method: string;
  readonly params?: Array<unknown>;
}

export interface WalletBridgeResponse {
  readonly result?: any;
  readonly error?: {
    readonly code: number;
    readonly message: string;
    readonly data?: any;
  };
}

export interface Listeners {
  onError: (backendOutput: string, code: BackendCode) => void;
  onAbout: () => void;
  onRestart: () => void;
  onMcpState?: (state: StarlingServiceStatus) => void;
  onOAuthCallback?: (oAuthResult: OAuthResult) => void;
  /**
   * Invoked when the main process is about to quit, before the backend
   * subprocesses are terminated. Gives the renderer a chance to swap in the
   * shutdown screen and stop talking to a backend that is going down.
   */
  onAppClosing?: () => void;
}

export interface Interop {
  openUrl: (url: string) => Promise<void>;
  openPath: (path: string) => Promise<void>;
  closeApp: () => Promise<void>;
  setListeners: (listeners: Listeners) => void;
  openDirectory: (title: string) => Promise<undefined | string>;
  premiumUserLoggedIn: (premiumUser: boolean) => void;
  debugSettings?: () => DebugSettings | undefined;
  /** The single origin the renderer addresses: core under `/api/1`, colibri under `/colibri`. */
  apiUrl: () => string;
  metamaskImport: () => Promise<MetamaskImport>;
  checkForUpdates: () => Promise<boolean>;
  downloadUpdate: (progress: (percentage: number) => void) => Promise<boolean>;
  installUpdate: () => Promise<boolean | Error>;
  restartBackend: (options: Partial<BackendOptions>, forceRestart?: boolean) => Promise<boolean>;
  setSelectedTheme: (selectedTheme: number) => Promise<boolean>;
  version: () => Promise<SystemVersion>;
  isMac: () => Promise<boolean>;
  config: (defaults: boolean) => Promise<Partial<BackendOptions>>;
  updateTray: (trayUpdate: TrayUpdate) => void;
  logToFile: (level: LogLevel, message: string) => void;
  setLogLevel: (level: LogLevel) => void;
  storePassword: (credentials: Credentials) => Promise<boolean>;
  getPassword: (username: string) => Promise<string>;
  clearPassword: () => Promise<void>;
  getMcpServerStatus: () => Promise<McpServerStatus>;
  setMcpAutoStart: (enabled: boolean) => Promise<McpServerStatus>;
  startMcpServer: () => Promise<McpServerStatus>;
  stopMcpServer: () => Promise<McpServerStatus>;
  resetMcpSession: () => Promise<void>;
  openWalletConnectBridge: () => Promise<void>;
  notifyUserLogout: () => void;
  /** Synchronously get any startup error that occurred before the renderer was ready */
  getStartupError: () => StartupError | null;
}
