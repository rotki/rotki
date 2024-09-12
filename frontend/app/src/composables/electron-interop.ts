import type { BackendOptions, Listeners, SystemVersion, TrayUpdate } from '@shared/ipc';
import type { WebVersion } from '@/types';

interface UseInteropReturn {
  readonly isPackaged: boolean;
  readonly appSession: boolean;
  logToFile: (message: string) => void;
  navigate: (url: string) => void;
  navigateToPremium: () => void;
  setupListeners: (listeners: Listeners) => void;
  openDirectory: (title: string) => Promise<string | undefined>;
  openUrl: (url: string) => void;
  openPath: (path: string) => void;
  premiumUserLoggedIn: (premiumUser: boolean) => void;
  closeApp: () => void;
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
  /**
   * Electron attaches a path property to {@see File}. In normal DOM inside a browser this property does not exist.
   * The method will return the path if we are in app session and the property exists or it will return undefined.
   * It can be used to check if we will upload, or path the file.
   *
   * @param file The file we want to get the path.
   */
  getPath: (file: File) => string | undefined;
}

const electronApp = !!window.interop;

function isAppSession(): boolean {
  const { url } = getBackendUrl();
  return electronApp && !url;
}

const interop = {
  get isPackaged(): boolean {
    return electronApp;
  },

  get appSession(): boolean {
    return isAppSession();
  },

  logToFile: (message: string): void => {
    window.interop?.logToFile(message);
  },

  navigate: (url: string): void => {
    window.interop?.openUrl(url);
  },

  navigateToPremium: (): void => {
    window.interop?.openUrl(externalLinks.premium);
  },

  setupListeners: (listeners: Listeners): void => {
    window.interop?.setListeners(listeners);
  },

  openDirectory: async (title: string): Promise<string | undefined> =>
    (await window.interop?.openDirectory(title)) ?? undefined,

  openUrl: (url: string): void => {
    electronApp ? window.interop?.openUrl(url) : window.open(url, '_blank');
  },

  openPath: (path: string): void => {
    window.interop?.openPath(path);
  },

  premiumUserLoggedIn: (premiumUser: boolean): void => {
    window.interop?.premiumUserLoggedIn(premiumUser);
  },

  closeApp: (): void => {
    window.interop?.closeApp();
  },

  metamaskImport: async (): Promise<string[]> => {
    if (!window.interop)
      throw new Error('environment does not support interop');

    const response = await window.interop.metamaskImport();

    if ('error' in response)
      throw new Error(response.error);

    return response.addresses;
  },

  restartBackend: async (options: Partial<BackendOptions>): Promise<boolean> => {
    assert(window.interop);
    return await window.interop.restartBackend(options);
  },

  config: async (defaults: boolean): Promise<Partial<BackendOptions>> => {
    assert(window.interop);
    return await window.interop.config(defaults);
  },

  version: (): Promise<SystemVersion | WebVersion> => {
    if (!window.interop) {
      return Promise.resolve({
        platform: navigator?.platform,
        userAgent: navigator?.userAgent,
      });
    }
    return window.interop?.version();
  },

  isMac: (): Promise<boolean> => Promise.resolve(window.interop?.isMac() || navigator.platform?.startsWith?.('Mac')),

  resetTray: (): void => {
    window.interop?.updateTray({});
  },

  updateTray: (update: TrayUpdate): void => {
    window.interop?.updateTray(update);
  },

  storePassword: async (username: string, password: string): Promise<boolean | undefined> => {
    assert(window.interop);
    return await window.interop.storePassword(username, password);
  },

  getPassword: async (username: string): Promise<string | undefined> => {
    assert(window.interop);
    return await window.interop.getPassword(username);
  },

  clearPassword: async (): Promise<void> => {
    await window.interop?.clearPassword();
  },

  checkForUpdates: async (): Promise<boolean> => (await window.interop?.checkForUpdates()) ?? false,

  downloadUpdate: async (progress: (percentage: number) => void): Promise<boolean> =>
    (await window.interop?.downloadUpdate(progress)) ?? false,

  installUpdate: async (): Promise<boolean | Error> => (await window.interop?.installUpdate()) ?? false,

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
};

export const useInterop = (): UseInteropReturn => interop;
