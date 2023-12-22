import {
  type BackendOptions,
  type Listeners,
  type SystemVersion,
  type TrayUpdate
} from '@/electron-main/ipc';
import { type WebVersion } from '@/types';
import { externalLinks } from '@/data/external-links';

const electronApp = !!window.interop;

const interop = {
  get isPackaged(): boolean {
    return electronApp;
  },

  get appSession(): boolean {
    const { url } = getBackendUrl();
    return electronApp && !url;
  },

  logToFile: (message: string): void => {
    window.interop?.logToFile(message);
  },

  navigate: (url: string): void => {
    window.interop?.openUrl(url);
  },

  navigateToPremium: () => {
    window.interop?.openUrl(externalLinks.premium);
  },

  setupListeners: (listeners: Listeners) => {
    window.interop?.setListeners(listeners);
  },

  openDirectory: async (title: string): Promise<string | undefined> =>
    (await window.interop?.openDirectory(title)) ?? undefined,

  openUrl: (url: string) => {
    electronApp ? window.interop?.openUrl(url) : window.open(url, '_blank');
  },

  openPath: (path: string) => {
    window.interop?.openPath(path);
  },

  premiumUserLoggedIn: (premiumUser: boolean) => {
    window.interop?.premiumUserLoggedIn(premiumUser);
  },

  closeApp: () => {
    window.interop?.closeApp();
  },

  metamaskImport: async (): Promise<string[]> => {
    if (!window.interop) {
      throw new Error('environment does not support interop');
    }
    return window.interop.metamaskImport().then(value => {
      if ('error' in value) {
        throw new Error(value.error);
      }
      return value.addresses;
    });
  },

  restartBackend: async (
    options: Partial<BackendOptions>
  ): Promise<boolean> => {
    assert(window.interop);
    return await window.interop.restartBackend(options);
  },

  config: async (defaults: boolean): Promise<Partial<BackendOptions>> => {
    assert(window.interop);
    return await window.interop.config(defaults);
  },

  version: async (): Promise<SystemVersion | WebVersion> => {
    if (!window.interop) {
      return {
        platform: navigator?.platform,
        userAgent: navigator?.userAgent
      };
    }
    return window.interop?.version();
  },

  isMac: async (): Promise<boolean> =>
    window.interop?.isMac() || navigator.platform?.startsWith?.('Mac'),

  resetTray: () => {
    window.interop?.updateTray({});
  },

  updateTray: (update: TrayUpdate) => {
    window.interop?.updateTray(update);
  },

  storePassword: async (
    username: string,
    password: string
  ): Promise<boolean | undefined> => {
    assert(window.interop);
    return await window.interop.storePassword(username, password);
  },

  getPassword: async (username: string): Promise<string | undefined> => {
    assert(window.interop);
    return await window.interop.getPassword(username);
  },

  clearPassword: async () => {
    await window.interop?.clearPassword();
  },

  checkForUpdates: async () =>
    (await window.interop?.checkForUpdates()) ?? false,

  downloadUpdate: async (
    progress: (percentage: number) => void
  ): Promise<boolean> =>
    (await window.interop?.downloadUpdate(progress)) ?? false,

  installUpdate: async (): Promise<boolean | Error> =>
    (await window.interop?.installUpdate()) ?? false
};

export const useInterop = () => interop;
