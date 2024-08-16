import fs from 'node:fs';
import path from 'node:path';
import { type App, app } from 'electron';

class SettingManager {
  private readonly _appSettings: SettingsManager = {
    displayTray: true,
  };

  constructor(private app: App) {
    this._appSettings = this.readAppSettings();
  }

  get appSettings(): SettingsManager {
    return this._appSettings;
  }

  private appConfigFile() {
    const userData = this.app.getPath('userData');
    return path.join(userData, 'app.config.json');
  }

  private writeAppSettings(settings: SettingsManager) {
    const appConfig = this.appConfigFile();
    const json = JSON.stringify(settings);
    try {
      fs.writeFileSync(appConfig, json, { encoding: 'utf8' });
    }
    catch (error: any) {
      console.error(error, 'Could not write the app settings file');
    }
  }

  private readAppSettings(): SettingsManager {
    const settings: SettingsManager = {
      displayTray: true,
    };
    const appConfig = this.appConfigFile();
    if (fs.existsSync(appConfig)) {
      try {
        const file = fs.readFileSync(appConfig, { encoding: 'utf8' });
        const loadedSettings = JSON.parse(file) as Partial<SettingsManager>;
        for (const [key, value] of Object.entries(loadedSettings)) {
          if (typeof settings[key as keyof SettingsManager] === typeof value) {
            // @ts-expect-error any type
            settings[key] = loadedSettings[key];
          }
        }
      }
      catch (error: any) {
        console.error(error);
      }
    }

    return settings;
  }

  save() {
    this.writeAppSettings(this._appSettings);
  }
}

export interface SettingsManager {
  displayTray: boolean;
}

export const settingsManager = new SettingManager(app);
