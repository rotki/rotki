export type DebugSettings = { vuex: boolean };

type MetamaskImportError = {
  readonly error: string;
};
type MetamaskImportSupport = {
  readonly addresses: string[];
};
type MetamaskImport = MetamaskImportError | MetamaskImportSupport;

interface Interop {
  openUrl(url: string): Promise<void>;
  closeApp(): void;
  listenForErrors(callback: (backendOutput: string) => void): void;
  openFile(title: string): Promise<undefined | string>;
  openDirectory(title: string): Promise<undefined | string>;
  premiumUserLoggedIn(premiumUser: boolean): Promise<undefined | boolean>;
  monitorDebugSettings(): void;
  debugSettings?(): DebugSettings | undefined;
  serverUrl(): string;
  metamaskImport(): Promise<MetamaskImport>;
}

declare global {
  interface Window {
    interop?: Interop;
  }
}

export type Writeable<T> = { -readonly [P in keyof T]: T[P] };

export type Properties<TObj, TResult> = {
  [K in keyof TObj]: TObj[K] extends TResult ? K : never;
}[keyof TObj];
