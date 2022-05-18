import { getBackendUrl } from '@/components/account-management/utils';
import { BackendCode } from '@/electron-main/backend-code';
import { BackendOptions, SystemVersion, TrayUpdate } from '@/electron-main/ipc';
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

  navigateToRotki() {
    window.interop?.openUrl(this.baseUrl);
  }

  onError(callback: (backendOutput: string, code: BackendCode) => void) {
    window.interop?.listenForErrors(callback);
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
        platform: navigator.platform,
        userAgent: navigator.userAgent
      };
    }
    return window.interop?.version();
  }

  async isMac(): Promise<boolean> {
    const version = await this.version();

    return (
      (version as SystemVersion)?.os === 'darwin' ||
      (version as WebVersion)?.platform?.startsWith?.('Mac')
    );
  }

  onAbout(cb: () => void) {
    window.interop?.onAbout(cb);
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
    window.interop?.clearPassword();
  }
}

export const interop = new ElectronInterop();

export const useInterop = () => interop;
