import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { MenuItemConstructorOptions } from 'electron';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MenuManager } from './menu';

// The menu is built once and handed to electron, so the template is the only place a
// test can read what an entry will do. `buildFromTemplate` captures it; nothing else
// of electron is exercised here.
const { buildFromTemplateMock, getPathMock, openPathMock } = vi.hoisted(() => ({
  buildFromTemplateMock: vi.fn<(template: MenuItemConstructorOptions[]) => unknown>(),
  getPathMock: vi.fn<(name: string) => string>(),
  openPathMock: vi.fn<(path: string) => Promise<string>>(),
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

  function submenuOf(label: string): MenuItemConstructorOptions[] {
    const menu = template.find(item => item.label === label);
    expect(menu?.submenu).toBeInstanceOf(Array);
    return Array.isArray(menu?.submenu) ? menu.submenu : [];
  }

  beforeEach(() => {
    vi.clearAllMocks();
    getPathMock.mockReturnValue(DEFAULT_LOGS);
    openPathMock.mockResolvedValue('');
    buildFromTemplateMock.mockImplementation((built) => {
      template = built;
      return { getMenuItemById: (): undefined => undefined, removeAllListeners: vi.fn() };
    });

    const logger = createMock<LogService>({ logDirectory: CONFIGURED_LOGS });
    const settings = createMock<SettingsManager>({ appSettings: { displayTray: false, persistStore: false } });
    // Booleans left off a `createMock` proxy read back truthy, so both platform gates
    // are set explicitly — otherwise the template grows the mac and debug menus.
    const config = createMock<AppConfig>({ isDev: false, isMac: false });

    new MenuManager(logger, settings, config).initialize({ onDisplayTrayChanged: vi.fn() });
  });

  it('should open the configured log directory, not the platform default', () => {
    const item = submenuOf('&Help').find(entry => entry.label === 'Logs Directory');
    expect(item).toBeDefined();

    item?.click?.(createMock(), undefined, createMock());

    expect(openPathMock).toHaveBeenCalledWith(CONFIGURED_LOGS);
    expect(openPathMock).not.toHaveBeenCalledWith(DEFAULT_LOGS);
  });
});
