import { shell } from 'electron';

export class ElectronInterop {
  private packagedApp: boolean = true;
  private _premiumURL: string = 'https://rotki.com/products/';

  get premiumURL(): string {
    return this._premiumURL;
  }

  get isPackaged(): boolean {
    return this.packagedApp;
  }

  upgradePremium() {
    shell.openExternal(this._premiumURL);
  }
}

export const interop = new ElectronInterop();
