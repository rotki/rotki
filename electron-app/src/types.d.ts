export interface Interop {
  openUrl(url: string): Promise<void>;
  closeApp(): void;
  listenForErrors(callback: () => void): void;
  openFile(title: string): Promise<undefined | string>;
  openDirectory(title: string): Promise<undefined | string>;
  premiumUserLoggedIn(premiumUser: boolean): Promise<undefined | boolean>;
}

declare global {
  interface Window {
    interop?: Interop;
  }
}
