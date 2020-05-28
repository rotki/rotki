export class ElectronInterop {
  private packagedApp: boolean = !!window.interop;
  readonly baseUrl = 'https://rotki.com';
  readonly baseDocsUrl = 'https://rotki.readthedocs.io';
  readonly premiumURL: string = `${this.baseUrl}/products/`;
  readonly usageGuideURL: string = `${this.baseDocsUrl}/en/stable/usage_guide.html`;

  get isPackaged(): boolean {
    return this.packagedApp;
  }

  navigateToPremium() {
    window.interop?.openUrl(this.premiumURL);
  }

  navigateToRotki() {
    window.interop?.openUrl(this.baseUrl);
  }

  onError(callback: () => void) {
    window.interop?.listenForErrors(callback);
  }

  async openDirectory(title: string): Promise<string | undefined> {
    return (await window.interop?.openDirectory(title)) ?? undefined;
  }

  async openFile(title: string): Promise<string | undefined> {
    return (await window.interop?.openFile(title)) ?? undefined;
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
}

export const interop = new ElectronInterop();
