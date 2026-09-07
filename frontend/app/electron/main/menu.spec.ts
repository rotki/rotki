import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { MenuItemConstructorOptions } from 'electron';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { MenuManager } from './menu';

// `buildFromTemplate` captures the template, the only place a test can read what an entry does.
const { buildFromTemplateMock, getPathMock, openPathMock, statSyncMock } = vi.hoisted(() => ({
  buildFromTemplateMock: vi.fn<(template: MenuItemConstructorOptions[]) => unknown>(),
  getPathMock: vi.fn<(name: string) => string>(),
  openPathMock: vi.fn<(path: string) => Promise<string>>(),
  statSyncMock: vi.fn<(path: string) => { isDirectory: () => boolean }>(),
}));

vi.mock('electron', () => ({
  app: { getPath: getPathMock, name: 'rotki' },
  BrowserWindow: class {},
  Menu: {
    buildFromTemplate: buildFromTemplateMock,
    setApplicationMenu: vi.fn(),
  },
  shell: { openExternal: vi.fn(), openPath: openPathMock },
}));

vi.mock('node:fs', () => ({ default: { statSync: statSyncMock } }));

/**
 * The one seam this spec covers: Help ▸ Logs Directory must open the directory the
 * running app actually logs to, which `LogService` owns and can reconfigure, not the
 * platform default. The two differ exactly when a user sets a custom log directory —
 * so the fixture keeps them different on purpose.
 */
describe('menuManager', () => {
  const DEFAULT_LOGS = '/home/user/.config/rotki/logs';
  const CONFIGURED_LOGS = '/mnt/custom/rotki-logs';

  let template: MenuItemConstructorOptions[];
  let dataDirectoryItem: { enabled: boolean };
  let manager: MenuManager;
  let logError: Mock<LogService['error']>;

  function submenuOf(label: string): MenuItemConstructorOptions[] {
    const menu = template.find(item => item.label === label);
    expect(menu?.submenu).toBeInstanceOf(Array);
    return Array.isArray(menu?.submenu) ? menu.submenu : [];
  }

  function clickHelpEntry(label: string): void {
    const item = submenuOf('&Help').find(entry => entry.label === label);
    expect(item).toBeDefined();
    item?.click?.(createMock(), undefined, createMock());
  }

  beforeEach(() => {
    vi.clearAllMocks();
    getPathMock.mockReturnValue(DEFAULT_LOGS);
    openPathMock.mockResolvedValue('');
    statSyncMock.mockReturnValue({ isDirectory: () => true });
    dataDirectoryItem = { enabled: false };
    buildFromTemplateMock.mockImplementation((built) => {
      template = built;
      return { getMenuItemById: () => dataDirectoryItem, removeAllListeners: vi.fn() };
    });

    logError = vi.fn<LogService['error']>();
    const logger = createMock<LogService>({ logDirectory: CONFIGURED_LOGS, error: logError });
    const settings = createMock<SettingsManager>({ appSettings: { displayTray: false, persistStore: false } });
    // Booleans left off a `createMock` proxy read back truthy, so both platform gates are explicit.
    const config = createMock<AppConfig>({ isDev: false, isMac: false });

    manager = new MenuManager(logger, settings, config);
    manager.initialize({ onDisplayTrayChanged: vi.fn() });
  });

  it('should open the configured log directory, not the platform default', () => {
    clickHelpEntry('Logs Directory');

    expect(openPathMock).toHaveBeenCalledWith(CONFIGURED_LOGS);
    expect(openPathMock).not.toHaveBeenCalledWith(DEFAULT_LOGS);
  });

  it('should log the message openPath resolves with, which is how it reports a failure', async () => {
    openPathMock.mockResolvedValue('no application is registered');

    clickHelpEntry('Logs Directory');
    await vi.waitFor(() => expect(logError).toHaveBeenCalled());

    expect(logError).toHaveBeenCalledWith(expect.stringContaining('no application is registered'));
  });

  it('should not log when openPath resolves with the empty string it uses for success', async () => {
    const opened = Promise.resolve('');
    openPathMock.mockReturnValue(opened);

    clickHelpEntry('Logs Directory');
    await opened;
    await Promise.resolve();

    expect(logError).not.toHaveBeenCalled();
  });

  describe('setDataDirectory', () => {
    it('should enable the entry for a real directory', () => {
      manager.setDataDirectory('/mnt/rotki-data');

      expect(dataDirectoryItem.enabled).toBe(true);
    });

    it('should leave the entry disabled for a path that names a file, which openPath would open', () => {
      statSyncMock.mockReturnValue({ isDirectory: () => false });

      manager.setDataDirectory('/mnt/rotki-data/rotkehlchen.db');

      expect(dataDirectoryItem.enabled).toBe(false);
    });

    it('should leave the entry disabled for a path that cannot be stat-ed', () => {
      statSyncMock.mockImplementation(() => {
        throw new Error('ENOENT');
      });

      manager.setDataDirectory('/gone');

      expect(dataDirectoryItem.enabled).toBe(false);
    });

    it('should disable the entry again when the backend goes away', () => {
      manager.setDataDirectory('/mnt/rotki-data');

      manager.setDataDirectory('');

      expect(dataDirectoryItem.enabled).toBe(false);
    });
  });
});
