import {
  BackendOptions,
  Listeners,
  SystemVersion,
  TrayUpdate
} from '@/electron-main/ipc';
import { WebVersion } from '@/types';
import { getBackendUrl } from '@/utils/account-management';
import { assert } from '@/utils/assertions';

const BASEURL = 'https://rotki.com/';
const BASE_DOCS_URL = 'https://rotki.readthedocs.io';
const premiumURL = `${BASEURL}products/`;
const electronApp = !!window.interop;

export const interop = {
  get premiumURL() {
    return premiumURL;
  },
  get usageGuideURL() {
    return `${BASE_DOCS_URL}/en/stable/usage_guide.html`;
  },
  get contributeUrl() {
    return `${BASE_DOCS_URL}/en/stable/contribute.html`;
  },
  get coingeckoContributeUrl() {
    return `${this.contributeUrl}#get-coingecko-asset-identifier`;
  },
  get cryptocompareContributeUrl() {
    return `${this.contributeUrl}#get-cryptocompare-asset-identifier`;
  },
  get languageContributeUrl() {
    return `${this.contributeUrl}#add-a-new-language-or-translation`;
  },
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
    window.interop?.openUrl(premiumURL);
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
