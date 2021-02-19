import { TimeUnit } from '@/components/dashboard/types';
import { Level } from '@/utils/log-level';

export const IPC_RESTART_BACKEND = 'RESTART_BACKEND' as const;
export const IPC_CHECK_FOR_UPDATES = 'CHECK_FOR_UPDATES' as const;
export const IPC_DOWNLOAD_UPDATE = 'DOWNLOAD_UPDATE' as const;
export const IPC_INSTALL_UPDATE = 'INSTALL_UPDATE' as const;

export type DebugSettings = { vuex: boolean };

interface DateUtilities {
  epoch(): number;
  format(date: string, oldFormat: string, newFormat: string): string;
  now(format: string): string;
  epochToFormat(epoch: number, format: string): string;
  dateToEpoch(date: string, format: string): number;
  epochStartSubtract(amount: number, unit: TimeUnit): number;
}

export type ExposedUtilities = {
  readonly date: DateUtilities;
};

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
  listenForErrors(callback: (backendOutput: string) => void): void;
  openDirectory(title: string): Promise<undefined | string>;
  premiumUserLoggedIn(premiumUser: boolean): Promise<undefined | boolean>;
  monitorDebugSettings(): void;
  debugSettings?(): DebugSettings | undefined;
  serverUrl(): string;
  metamaskImport(): Promise<MetamaskImport>;
  checkForUpdates(): Promise<boolean>;
  downloadUpdate(): Promise<boolean>;
  installUpdate(): Promise<void>;
  restartBackend(logLevel: Level): Promise<boolean>;
}
