import type { App } from 'electron';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { SettingsManager } from './settings-manager';

describe('settingsManager', () => {
  let directory: string;
  let app: App;

  beforeEach(() => {
    directory = fs.mkdtempSync(path.join(os.tmpdir(), 'rotki-settings-'));
    app = createMock<App>({ getPath: () => directory });
  });

  afterEach(() => {
    fs.rmSync(directory, { force: true, recursive: true });
  });

  function writeSettings(contents: unknown): void {
    fs.writeFileSync(path.join(directory, 'app.config.json'), JSON.stringify(contents), { encoding: 'utf8' });
  }

  it('should apply the defaults when no file exists', () => {
    expect(new SettingsManager(app).appSettings).toStrictEqual({
      displayTray: true,
      mcpAutoStart: false,
      showNetWorthOnTray: false,
    });
  });

  it('should read the stored settings', () => {
    writeSettings({ displayTray: false, mcpAutoStart: true, persistStore: true, showNetWorthOnTray: true });

    expect(new SettingsManager(app).appSettings).toStrictEqual({
      displayTray: false,
      mcpAutoStart: true,
      persistStore: true,
      showNetWorthOnTray: true,
    });
  });

  it('should default the keys a stored file omits', () => {
    // The tray defaults to on, so a file predating the setting must not silently disable it.
    writeSettings({ mcpAutoStart: true });
    const settings = new SettingsManager(app).appSettings;

    expect(settings.displayTray).toBe(true);
    expect(settings.showNetWorthOnTray).toBe(false);
    expect(settings.mcpAutoStart).toBe(true);
  });

  it('should leave persistStore unset when the file omits it', () => {
    writeSettings({ displayTray: true });

    expect(new SettingsManager(app).appSettings.persistStore).toBeUndefined();
  });

  it('should fall back to the defaults when the file is corrupt', () => {
    fs.writeFileSync(path.join(directory, 'app.config.json'), 'not json', { encoding: 'utf8' });

    expect(new SettingsManager(app).appSettings.displayTray).toBe(true);
  });

  it('should fall back to the defaults when a value has the wrong type', () => {
    writeSettings({ displayTray: 'yes' });

    expect(new SettingsManager(app).appSettings.displayTray).toBe(true);
  });

  it('should persist a change so a later instance reads it', () => {
    const manager = new SettingsManager(app);
    manager.setMcpAutoStart(true);

    expect(new SettingsManager(app).appSettings.mcpAutoStart).toBe(true);
  });

  it('should persist edits made through appSettings on save', () => {
    const manager = new SettingsManager(app);
    manager.appSettings.showNetWorthOnTray = true;
    manager.save();

    expect(new SettingsManager(app).appSettings.showNetWorthOnTray).toBe(true);
  });
});
