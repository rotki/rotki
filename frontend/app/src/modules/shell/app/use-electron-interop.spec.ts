import type { Interop, SystemVersion } from '@shared/ipc';
import { externalLinks } from '@shared/external-links';
import { LogLevel } from '@shared/log-level';
import { createMock, type DeepPartial } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

type UseInterop = ReturnType<(typeof import('./use-electron-interop'))['useInterop']>;

const systemVersion: SystemVersion = { arch: 'x64', electron: '30.0.0', os: 'linux', osVersion: '6.0' };

function makeInterop(overrides?: DeepPartial<Interop>): Interop {
  return createMock<Interop>({
    checkForUpdates: vi.fn().mockResolvedValue(true),
    clearPassword: vi.fn().mockResolvedValue(undefined),
    closeApp: vi.fn().mockResolvedValue(undefined),
    config: vi.fn().mockResolvedValue({ dataDirectory: '/data' }),
    downloadUpdate: vi.fn().mockResolvedValue(true),
    getPassword: vi.fn().mockResolvedValue('secret'),
    getStartupError: vi.fn().mockReturnValue(null),
    installUpdate: vi.fn().mockResolvedValue(true),
    isMac: vi.fn().mockResolvedValue(true),
    logToFile: vi.fn(),
    metamaskImport: vi.fn().mockResolvedValue({ addresses: ['0xabc'] }),
    notifyUserLogout: vi.fn(),
    openDirectory: vi.fn().mockResolvedValue('/selected'),
    openPath: vi.fn().mockResolvedValue(undefined),
    openUrl: vi.fn().mockResolvedValue(undefined),
    premiumUserLoggedIn: vi.fn(),
    restartBackend: vi.fn().mockResolvedValue(true),
    setListeners: vi.fn(),
    setLogLevel: vi.fn(),
    setSelectedTheme: vi.fn().mockResolvedValue(true),
    storePassword: vi.fn().mockResolvedValue(true),
    updateTray: vi.fn(),
    version: vi.fn().mockResolvedValue(systemVersion),
    ...overrides,
  });
}

async function loadInterop(interop?: Interop): Promise<UseInterop> {
  vi.resetModules();
  if (interop)
    window.interop = interop;
  else
    Reflect.deleteProperty(window, 'interop');

  const { useInterop } = await import('./use-electron-interop');
  return useInterop();
}

describe('useInterop', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    Reflect.deleteProperty(window, 'interop');
  });

  describe('environment flags', () => {
    it('should report isPackaged/appSession true inside electron without a backend url', async () => {
      const interop = await loadInterop(makeInterop());
      expect(interop.isPackaged).toBe(true);
      expect(interop.appSession).toBe(true);
    });

    it('should report appSession false when a backend url is configured', async () => {
      localStorage.setItem('rotki.backend_url', 'http://localhost:4242');
      const interop = await loadInterop(makeInterop());
      expect(interop.isPackaged).toBe(true);
      expect(interop.appSession).toBe(false);
    });

    it('should report isPackaged/appSession false outside electron', async () => {
      const interop = await loadInterop();
      expect(interop.isPackaged).toBe(false);
      expect(interop.appSession).toBe(false);
    });
  });

  describe('update flow', () => {
    it('should delegate checkForUpdates/downloadUpdate/installUpdate to interop', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      const progress = vi.fn();

      expect(await interop.checkForUpdates()).toBe(true);
      expect(await interop.downloadUpdate(progress)).toBe(true);
      expect(await interop.installUpdate()).toBe(true);
      expect(mock.downloadUpdate).toHaveBeenCalledWith(progress);
    });

    it('should fall back to false when interop is unavailable', async () => {
      const interop = await loadInterop();
      expect(await interop.checkForUpdates()).toBe(false);
      expect(await interop.downloadUpdate(vi.fn())).toBe(false);
      expect(await interop.installUpdate()).toBe(false);
    });
  });

  describe('passwords', () => {
    it('should store and read passwords through interop', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);

      expect(await interop.storePassword('user', 'pass')).toBe(true);
      expect(mock.storePassword).toHaveBeenCalledWith({ password: 'pass', username: 'user' });
      expect(await interop.getPassword('user')).toBe('secret');
      await interop.clearPassword();
      expect(mock.clearPassword).toHaveBeenCalled();
    });

    it('should return undefined from getPassword outside electron', async () => {
      const interop = await loadInterop();
      expect(await interop.getPassword('user')).toBeUndefined();
    });

    it('should throw from storePassword outside electron', async () => {
      const interop = await loadInterop();
      await expect(interop.storePassword('user', 'pass')).rejects.toThrow();
    });
  });

  describe('navigation and urls', () => {
    it('should open urls via interop inside electron', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      await interop.openUrl('https://rotki.com');
      expect(mock.openUrl).toHaveBeenCalledWith('https://rotki.com');
    });

    it('should open urls in a new tab outside electron', async () => {
      const open = vi.spyOn(window, 'open').mockReturnValue(null);
      const interop = await loadInterop();
      await interop.openUrl('https://rotki.com');
      expect(open).toHaveBeenCalledWith('https://rotki.com', '_blank');
      open.mockRestore();
    });

    it('should navigate and navigateToPremium through interop.openUrl', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      await interop.navigate('https://example.com');
      await interop.navigateToPremium();
      expect(mock.openUrl).toHaveBeenNthCalledWith(1, 'https://example.com');
      expect(mock.openUrl).toHaveBeenNthCalledWith(2, externalLinks.premium);
    });

    it('should forward openDirectory/openPath results', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      expect(await interop.openDirectory('pick')).toBe('/selected');
      await interop.openPath('/some/path');
      expect(mock.openPath).toHaveBeenCalledWith('/some/path');
    });
  });

  describe('metamask import', () => {
    it('should return the imported addresses', async () => {
      const interop = await loadInterop(makeInterop());
      expect(await interop.metamaskImport()).toEqual(['0xabc']);
    });

    it('should throw the reported import error', async () => {
      const interop = await loadInterop(makeInterop({
        metamaskImport: vi.fn().mockResolvedValue({ error: 'no metamask' }),
      }));
      await expect(interop.metamaskImport()).rejects.toThrow('no metamask');
    });

    it('should throw when interop is unavailable', async () => {
      const interop = await loadInterop();
      await expect(interop.metamaskImport()).rejects.toThrow('environment does not support interop');
    });
  });

  describe('config and backend', () => {
    it('should return config and restart the backend through interop', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      expect(await interop.config(true)).toEqual({ dataDirectory: '/data' });
      expect(mock.config).toHaveBeenCalledWith(true);
      expect(await interop.restartBackend({ dataDirectory: '/x' })).toBe(true);
      expect(mock.restartBackend).toHaveBeenCalledWith({ dataDirectory: '/x' }, false);
    });

    it('should throw from config outside electron', async () => {
      const interop = await loadInterop();
      await expect(interop.config(true)).rejects.toThrow();
    });
  });

  describe('version and platform', () => {
    it('should return the system version inside electron', async () => {
      const interop = await loadInterop(makeInterop());
      expect(await interop.version()).toEqual(systemVersion);
      expect(await interop.isMac()).toBe(true);
    });

    it('should return a web version outside electron', async () => {
      const interop = await loadInterop();
      const version = await interop.version();
      expect(version).toHaveProperty('platform');
      expect(version).toHaveProperty('userAgent');
    });
  });

  describe('file path resolution', () => {
    it('should return the electron path attached to a file', async () => {
      const interop = await loadInterop(makeInterop());
      const file = Object.assign(new File([], 'a.txt'), { path: '/tmp/a.txt' });
      expect(interop.getPath(file)).toBe('/tmp/a.txt');
    });

    it('should return undefined for a plain browser file', async () => {
      const interop = await loadInterop(makeInterop());
      expect(interop.getPath(new File([], 'a.txt'))).toBeUndefined();
    });

    it('should return undefined when not in an app session', async () => {
      localStorage.setItem('rotki.backend_url', 'http://localhost:4242');
      const interop = await loadInterop(makeInterop());
      const file = Object.assign(new File([], 'a.txt'), { path: '/tmp/a.txt' });
      expect(interop.getPath(file)).toBeUndefined();
    });
  });

  describe('tray, logging and listeners', () => {
    it('should reset and update the tray', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      interop.resetTray();
      interop.updateTray({ up: true });
      expect(mock.updateTray).toHaveBeenNthCalledWith(1, {});
      expect(mock.updateTray).toHaveBeenNthCalledWith(2, { up: true });
    });

    it('should forward logging and listener registration', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      interop.logToFile(LogLevel.INFO, 'hello');
      interop.setLogLevel(LogLevel.DEBUG);
      const listeners = { onAbout: vi.fn(), onError: vi.fn(), onProcessDetected: vi.fn(), onRestart: vi.fn() };
      interop.setupListeners(listeners);
      expect(mock.logToFile).toHaveBeenCalledWith(LogLevel.INFO, 'hello');
      expect(mock.setLogLevel).toHaveBeenCalledWith(LogLevel.DEBUG);
      expect(mock.setListeners).toHaveBeenCalledWith(listeners);
    });

    it('should forward premium status, logout, theme and closeApp', async () => {
      const mock = makeInterop();
      const interop = await loadInterop(mock);
      interop.premiumUserLoggedIn(true);
      interop.notifyUserLogout();
      await interop.setSelectedTheme(1);
      await interop.closeApp();
      expect(mock.premiumUserLoggedIn).toHaveBeenCalledWith(true);
      expect(mock.notifyUserLogout).toHaveBeenCalled();
      expect(mock.setSelectedTheme).toHaveBeenCalledWith(1);
      expect(mock.closeApp).toHaveBeenCalled();
    });
  });

  describe('startup error', () => {
    it('should return the startup error reported by interop', async () => {
      const interop = await loadInterop(makeInterop({
        getStartupError: vi.fn().mockReturnValue({ code: 0, message: 'boom' }),
      }));
      expect(interop.getStartupError()).toEqual({ code: 0, message: 'boom' });
    });

    it('should return null when interop is unavailable', async () => {
      const interop = await loadInterop();
      expect(interop.getStartupError()).toBeNull();
    });
  });
});
