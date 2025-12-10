import type { DebugSettings } from '@rotki/common';
import { LogLevel } from '@shared/log-level';
import z from 'zod/v4';

export const BackendCode = {
  TERMINATED: 0,
  MACOS_VERSION: 1,
  WIN_VERSION: 2,
};

export type BackendCode = typeof BackendCode[keyof typeof BackendCode];

export interface ApiUrls { coreApiUrl: string; colibriApiUrl: string }

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

export const ActiveLogLevel = z.preprocess(
  s => (typeof s === 'string' ? s.toLowerCase() : s),
  z.enum(LogLevel),
);

export const BackendOptions = z.object({
  loglevel: ActiveLogLevel.optional(),
  dataDirectory: z.string().optional(),
  logDirectory: z.string().optional(),
  sleepSeconds: z.number().nonnegative().optional(),
  logFromOtherModules: z.boolean().optional(),
  maxSizeInMbAllLogs: z.number().int().positive().optional(),
  sqliteInstructions: z.number().int().positive().optional(),
  maxLogfilesNum: z.number().int().positive().optional(),
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
  onProcessDetected: (pids: string[]) => void;
  onOAuthCallback?: (oAuthResult: OAuthResult) => void;
}

export interface Interop {
  openUrl: (url: string) => Promise<void>;
  openPath: (path: string) => Promise<void>;
  closeApp: () => Promise<void>;
  setListeners: (listeners: Listeners) => void;
  openDirectory: (title: string) => Promise<undefined | string>;
  premiumUserLoggedIn: (premiumUser: boolean) => void;
  debugSettings?: () => DebugSettings | undefined;
  apiUrls: () => ApiUrls;
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
  logToFile: (level: LogLevel, message: string) => void;
  storePassword: (credentials: Credentials) => Promise<boolean>;
  getPassword: (username: string) => Promise<string>;
  clearPassword: () => Promise<void>;
  openWalletConnectBridge: () => Promise<void>;
  notifyUserLogout: () => void;
}
