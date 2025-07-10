import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { BackendOptions, SystemVersion, TrayUpdate } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import process from 'node:process';
import { loadConfig } from '@electron/main/config';
import { assert, type DebugSettings } from '@rotki/common';
import { dialog, nativeTheme, shell } from 'electron';

interface SystemHandlersCallbacks {
  updateTray: (trayUpdate: TrayUpdate) => void;
  getProtocolRegistrationFailed: () => boolean;
  openOAuthInWindow: (url: string) => Promise<void>;
}

export class SystemHandlers {
  private callbacks: SystemHandlersCallbacks | null = null;

  private readonly version: SystemVersion = {
    os: process.platform,
    arch: process.arch,
    osVersion: process.getSystemVersion(),
    electron: process.versions.electron,
  };

  private get requireCallbacks(): SystemHandlersCallbacks {
    const callbacks = this.callbacks;
    assert(callbacks);
    return callbacks;
  }

  constructor(
    private readonly logger: LogService,
    private readonly settings: SettingsManager,
    private readonly config: AppConfig,
  ) {}

  initialize(callbacks: SystemHandlersCallbacks): void {
    this.callbacks = callbacks;
  }

  // System info handlers
  getDebugSettings = (): DebugSettings => ({ persistStore: this.settings.appSettings.persistStore ?? false });

  getApiUrls = () => this.config.urls;

  getVersion = (): SystemVersion => this.version;

  getIsMac = (): boolean => this.version.os === 'darwin';

  // Theme handling
  setSelectedTheme = (selectedTheme: number): boolean => {
    const themeSource = ['dark', 'system', 'light'] as const;
    nativeTheme.themeSource = themeSource[selectedTheme];
    return nativeTheme.shouldUseDarkColors;
  };

  // File system operations
  private readonly select = async (
    title: string,
    prop: 'openFile' | 'openDirectory',
    defaultPath?: string,
  ): Promise<string | undefined> => {
    const value = await dialog.showOpenDialog({
      title,
      defaultPath,
      properties: [prop],
    });

    if (value.canceled)
      return undefined;

    return value.filePaths?.[0];
  };

  openDirectory = async (title: string, defaultPath?: string): Promise<string | undefined> => {
    try {
      return await this.select(title, 'openDirectory', defaultPath);
    }
    catch (error: any) {
      console.error(error);
      return undefined;
    }
  };

  openPath = (path: string): void => {
    shell.openPath(path).catch(error => this.logger.error(error));
  };

  // URL handling
  openUrl = async (url: string): Promise<void> => {
    if (!url || typeof url !== 'string' || (!this.config.isDev && !url.startsWith('https://'))) {
      console.error(`Error: Requested to open untrusted URL: ${url} `);
      return;
    }

    // Check if this is a Google OAuth URL and protocol registration failed
    const isGoogleOAuthUrl = url.includes('rotki.com/oauth/google') || (url.includes('localhost') && url.includes('/oauth/google'));
    const protocolRegistrationFailed = this.requireCallbacks.getProtocolRegistrationFailed();

    if (isGoogleOAuthUrl && protocolRegistrationFailed) {
      this.logger.info('Protocol registration failed, opening Google OAuth URL in second window instead of external browser');
      await this.requireCallbacks.openOAuthInWindow(url);
      return;
    }

    await shell.openExternal(url);
  };

  // Config handling
  getConfig = async (defaultConfig: boolean): Promise<Partial<BackendOptions>> => {
    if (defaultConfig) {
      return { logDirectory: this.logger.defaultLogDirectory };
    }
    else {
      return loadConfig();
    }
  };

  // Tray handling
  updateTray = (trayUpdate: TrayUpdate): void => {
    this.requireCallbacks.updateTray(trayUpdate);
  };

  // Logging
  logToFile = (level: LogLevel, message: string): void => {
    this.logger.write(level, message);
  };
}
