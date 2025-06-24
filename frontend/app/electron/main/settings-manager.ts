import type { App } from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import { z } from 'zod/v4';

const AppSettingsSchema = z.object({
  displayTray: z.boolean().default(true),
  persistStore: z.boolean().optional(),
  showNetWorthOnTray: z.boolean().default(false),
});

export type AppSettings = z.infer<typeof AppSettingsSchema>;

export class SettingsManager {
  private readonly _appSettings: AppSettings = {
    displayTray: true,
    showNetWorthOnTray: false,
  };

  constructor(private readonly app: App) {
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
    }
    catch (error: any) {
      console.error(error, 'Could not write the app settings file');
    }
  }

  private readAppSettings(): AppSettings {
    const appConfig = this.appConfigFile();
    if (fs.existsSync(appConfig)) {
      try {
        const file = fs.readFileSync(appConfig, { encoding: 'utf8' });
        return AppSettingsSchema.parse(JSON.parse(file));
      }
      catch (error: any) {
        console.error(error);
      }
    }

    return AppSettingsSchema.parse({});
  }

  save() {
    this.writeAppSettings(this._appSettings);
  }
}
