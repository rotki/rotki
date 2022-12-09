import fs from 'node:fs';
import path from 'node:path';
import { type App, app } from 'electron';

class AppSettingManager {
  private readonly _appSettings: AppSettings = {
    displayTray: true
  };

  constructor(private app: App) {
    this._appSettings = this.readAppSettings();
  }

  get appSettings(): AppSettings {
    return this._appSettings;
  }

  private appConfigFile() {
    const userData = this.app.getPath('userData');
    return path.join(userData, 'app.config.json');
  }

  private writeAppSettings(settings: AppSettings) {
    const appConfig = this.appConfigFile();
    const json = JSON.stringify(settings);
    try {
      fs.writeFileSync(appConfig, json, { encoding: 'utf8' });
    } catch (e: any) {
      console.error(e, 'Could not write the app settings file');
    }
  }

  private readAppSettings(): AppSettings {
    const settings: AppSettings = {
      displayTray: true
    };
    const appConfig = this.appConfigFile();
    if (fs.existsSync(appConfig)) {
      try {
        const file = fs.readFileSync(appConfig, { encoding: 'utf8' });
        const loadedSettings = JSON.parse(file) as Partial<AppSettings>;
        for (const [key, value] of Object.entries(loadedSettings)) {
          if (typeof settings[key as keyof AppSettings] === typeof value) {
            // @ts-ignore
            settings[key] = loadedSettings[key];
          }
        }
      } catch (e: any) {
        console.error(e);
      }
    }

    return settings;
  }

  save() {
    this.writeAppSettings(this._appSettings);
  }
}

export interface AppSettings {
  displayTray: boolean;
}

export const settingsManager = new AppSettingManager(app);
