import { getBackendUrl } from '@/components/account-management/utils';
import {
  BackendOptions,
  Listeners,
  SystemVersion,
  TrayUpdate
} from '@/electron-main/ipc';
import { WebVersion } from '@/types';
import { assert } from '@/utils/assertions';

export class ElectronInterop {
  private packagedApp: boolean = !!window.interop;
  readonly baseUrl = 'https://rotki.com/';
  readonly baseDocsUrl = 'https://rotki.readthedocs.io';
  readonly premiumURL: string = `${this.baseUrl}products/`;
  readonly usageGuideURL: string = `${this.baseDocsUrl}/en/stable/usage_guide.html`;
  readonly contributeUrl: string = `${this.baseDocsUrl}/en/stable/contribute.html`;

  get isPackaged(): boolean {
    return this.packagedApp;
  }

  get appSession(): boolean {
    const { url } = getBackendUrl();
    return this.isPackaged && !url;
  }

  logToFile(message: string) {
    return window.interop?.logToFile(message);
  }

  navigate(url: string) {
    window.interop?.openUrl(url);
  }

  navigateToPremium() {
    window.interop?.openUrl(this.premiumURL);
  }

  setupListeners(listeners: Listeners) {
    window.interop?.setListeners(listeners);
  }

  async openDirectory(title: string): Promise<string | undefined> {
    return (await window.interop?.openDirectory(title)) ?? undefined;
  }

  openUrl(url: string) {
    this.isPackaged ? window.interop?.openUrl(url) : window.open(url, '_blank');
  }

  openPath(path: string) {
    window.interop?.openPath(path);
  }

  premiumUserLoggedIn(premiumUser: boolean) {
    window.interop?.premiumUserLoggedIn(premiumUser);
  }

  closeApp() {
    window.interop?.closeApp();
  }

  async metamaskImport(): Promise<string[]> {
    if (!window.interop) {
      throw new Error('environment does not support interop');
    }
    return window.interop.metamaskImport().then(value => {
      if ('error' in value) {
        throw new Error(value.error);
      }
      return value.addresses;
    });
  }

  async restartBackend(options: Partial<BackendOptions>): Promise<boolean> {
    assert(window.interop);
    return await window.interop.restartBackend(options);
  }

  async config(defaults: boolean): Promise<Partial<BackendOptions>> {
    assert(window.interop);
    return await window.interop.config(defaults);
  }

  async version(): Promise<SystemVersion | WebVersion> {
    if (!window.interop) {
      return {
        platform: navigator?.platform,
        userAgent: navigator?.userAgent
      };
    }
    return window.interop?.version();
  }

  async isMac(): Promise<boolean> {
    return window.interop?.isMac() || navigator.platform?.startsWith?.('Mac');
  }

  resetTray() {
    window.interop?.updateTray({});
  }

  updateTray(update: TrayUpdate) {
    window.interop?.updateTray(update);
  }

  async storePassword(
    username: string,
    password: string
  ): Promise<boolean | undefined> {
    assert(window.interop);
    return await window.interop.storePassword(username, password);
  }

  async getPassword(username: string): Promise<string | undefined> {
    assert(window.interop);
    return await window.interop.getPassword(username);
  }

  async clearPassword() {
    await window.interop?.clearPassword();
  }

  async checkForUpdates() {
    return (await window.interop?.checkForUpdates()) ?? false;
  }

  async downloadUpdate(
    progress: (percentage: number) => void
  ): Promise<boolean> {
    return (await window.interop?.downloadUpdate(progress)) ?? false;
  }

  async installUpdate(): Promise<boolean | Error> {
    return (await window.interop?.installUpdate()) ?? false;
  }
}

export const interop = new ElectronInterop();

export const useInterop = () => interop;
