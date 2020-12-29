import { assert } from '@/utils/assertions';
import { Level } from '@/utils/log-level';

export class ElectronInterop {
  private packagedApp: boolean = !!window.interop;
  readonly baseUrl = 'https://rotki.com/';
  readonly baseDocsUrl = 'https://rotki.readthedocs.io';
  readonly premiumURL: string = `${this.baseUrl}products/`;
  readonly usageGuideURL: string = `${this.baseDocsUrl}/en/stable/usage_guide.html`;

  get isPackaged(): boolean {
    return this.packagedApp;
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

  onError(callback: (backendOutput: string) => void) {
    window.interop?.listenForErrors(callback);
  }

  async openDirectory(title: string): Promise<string | undefined> {
    return (await window.interop?.openDirectory(title)) ?? undefined;
  }

  openUrl(url: string) {
    window.interop?.openUrl(url);
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

  async restartBackend(logLevel: Level): Promise<boolean> {
    assert(window.interop);
    return await window.interop.restartBackend(logLevel);
  }
}

export const interop = new ElectronInterop();
