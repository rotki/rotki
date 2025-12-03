import type { BackendOptions, Listeners, SystemVersion, TrayUpdate } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import type { WebVersion } from '@/types';
import { assert, type Theme } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { getBackendUrl } from '@/utils/account-management';

interface UseInteropReturn {
  readonly isPackaged: boolean;
  readonly appSession: boolean;
  logToFile: (level: LogLevel, message?: any, ...optionalParams: any[]) => void;
  navigate: (url: string) => Promise<void>;
  navigateToPremium: () => Promise<void>;
  setupListeners: (listeners: Listeners) => void;
  openDirectory: (title: string) => Promise<string | undefined>;
  openUrl: (url: string) => Promise<void>;
  openPath: (path: string) => Promise<void>;
  premiumUserLoggedIn: (premiumUser: boolean) => void;
  closeApp: () => Promise<void>;
  metamaskImport: () => Promise<string[]>;
  restartBackend: (options: Partial<BackendOptions>) => Promise<boolean>;
  config: (defaults: boolean) => Promise<Partial<BackendOptions>>;
  version: () => Promise<SystemVersion | WebVersion>;
  isMac: () => Promise<boolean>;
  resetTray: () => void;
  updateTray: (update: TrayUpdate) => void;
  storePassword: (username: string, password: string) => Promise<boolean | undefined>;
  getPassword: (username: string) => Promise<string | undefined>;
  clearPassword: () => Promise<void>;
  checkForUpdates: () => Promise<any>;
  downloadUpdate: (progress: (percentage: number) => void) => Promise<boolean>;
  installUpdate: () => Promise<boolean | Error>;
  notifyUserLogout: () => void;
  /**
   * Electron attaches a path property to {@see File}. In normal DOM inside a browser this property does not exist.
   * The method will return the path if we are in app session and the property exists or it will return undefined.
   * It can be used to check if we will upload, or path the file.
   *
   * @param file The file we want to get the path.
   */
  getPath: (file: File) => string | undefined;
  setSelectedTheme: (selectedTheme: Theme) => Promise<void>;
}

const electronApp = !!window.interop;

function isAppSession(): boolean {
  const { url } = getBackendUrl();
  return electronApp && !url;
}

const interop: UseInteropReturn = {
  get appSession(): boolean {
    return isAppSession();
  },

  checkForUpdates: async (): Promise<boolean> => (await window.interop?.checkForUpdates()) ?? false,

  clearPassword: async (): Promise<void> => {
    await window.interop?.clearPassword();
  },

  closeApp: async (): Promise<void> => {
    await window.interop?.closeApp();
  },

  config: async (defaults: boolean): Promise<Partial<BackendOptions>> => {
    assert(window.interop);
    return window.interop.config(defaults);
  },

  downloadUpdate: async (progress: (percentage: number) => void): Promise<boolean> =>
    (await window.interop?.downloadUpdate(progress)) ?? false,

  getPassword: async (username: string): Promise<string | undefined> => {
    if (!electronApp) {
      return undefined;
    }
    assert(window.interop);
    return window.interop.getPassword(username);
  },

  /**
   * Electron attaches a path property to {@see File}. In normal DOM inside a browser this property does not exist.
   * The method will return the path if we are in app session and the property exists or it will return undefined.
   * It can be used to check if we will upload, or path the file.
   *
   * @param file The file we want to get the path.
   */
  getPath: (file: File): string | undefined => {
    if (!isAppSession())
      return undefined;

    if ('path' in file && typeof file.path === 'string')
      return file.path;

    return undefined;
  },

  installUpdate: async (): Promise<boolean | Error> => (await window.interop?.installUpdate()) ?? false,

  isMac: async (): Promise<boolean> => Promise.resolve(window.interop?.isMac() || navigator.platform?.startsWith?.('Mac')),

  get isPackaged(): boolean {
    return electronApp;
  },

  logToFile: (level: LogLevel, message: string): void => {
    window.interop?.logToFile(level, message);
  },

  metamaskImport: async (): Promise<string[]> => {
    if (!window.interop)
      throw new Error('environment does not support interop');

    const response = await window.interop.metamaskImport();

    if ('error' in response)
      throw new Error(response.error);

    return response.addresses;
  },

  navigate: async (url: string): Promise<void> => {
    await window.interop?.openUrl(url);
  },

  navigateToPremium: async (): Promise<void> => {
    await window.interop?.openUrl(externalLinks.premium);
  },

  notifyUserLogout: (): void => {
    window.interop?.notifyUserLogout();
  },

  openDirectory: async (title: string): Promise<string | undefined> =>
    (await window.interop?.openDirectory(title)) ?? undefined,

  openPath: async (path: string): Promise<void> => {
    await window.interop?.openPath(path);
  },

  openUrl: async (url: string): Promise<void> => {
    if (electronApp) {
      await window.interop?.openUrl(url);
    }
    else {
      window.open(url, '_blank');
    }
  },

  premiumUserLoggedIn: (premiumUser: boolean): void => {
    window.interop?.premiumUserLoggedIn(premiumUser);
  },

  resetTray: (): void => {
    window.interop?.updateTray({});
  },

  restartBackend: async (options: Partial<BackendOptions>): Promise<boolean> => {
    assert(window.interop);
    return window.interop.restartBackend(options);
  },

  setSelectedTheme: async (selectedTheme: Theme): Promise<void> => {
    await window.interop?.setSelectedTheme(selectedTheme);
  },

  setupListeners: (listeners: Listeners): void => {
    window.interop?.setListeners(listeners);
  },

  storePassword: async (username: string, password: string): Promise<boolean | undefined> => {
    assert(window.interop);
    return window.interop.storePassword({ password, username });
  },

  updateTray: (update: TrayUpdate): void => {
    window.interop?.updateTray(update);
  },

  version: async (): Promise<SystemVersion | WebVersion> => {
    if (!window.interop) {
      return Promise.resolve({
        platform: navigator?.platform,
        userAgent: navigator?.userAgent,
      });
    }
    return window.interop?.version();
  },
};

export const useInterop = (): UseInteropReturn => interop;
