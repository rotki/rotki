import { createTestingPinia } from '@pinia/testing';
import { assert } from '@rotki/common';
import { LogLevel } from '@shared/log-level';
import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearUserOptions, saveUserOptions, useBackendManagement } from '@/composables/backend';
import { useInterop } from '@/composables/electron-interop';
import { useMainStore } from '@/store/main';
import { getBackendUrl } from '@/utils/account-management';

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue({
    isPackaged: true,
    restartBackend: vi.fn(),
    config: vi.fn(),
  }),
}));

vi.mock('@/utils/account-management', () => ({
  getBackendUrl: vi.fn().mockReturnValue({
    sessionOnly: true,
    url: '',
  }),
  deleteBackendUrl: vi.fn(),
}));

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

function getStoredOptions(): Record<string, unknown> | null {
  const raw = localStorage.getItem(BACKEND_OPTIONS);
  if (!raw)
    return null;
  return JSON.parse(raw);
}

describe('composables::backend', () => {
  beforeAll(() => {
    const pinia = createTestingPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.removeItem(BACKEND_OPTIONS);
  });

  afterEach(() => {
    localStorage.removeItem(BACKEND_OPTIONS);
  });

  describe('saveUserOptions', () => {
    it('should save options to localStorage', () => {
      saveUserOptions({ dataDirectory: '/test/data' });

      const stored = getStoredOptions();
      expect(stored).not.toBeNull();
      expect(stored!.dataDirectory).toBe('/test/data');
    });

    it('should merge new options with existing ones', () => {
      saveUserOptions({ dataDirectory: '/test/data' });
      saveUserOptions({ loglevel: LogLevel.DEBUG });

      const stored = getStoredOptions();
      expect(stored!.dataDirectory).toBe('/test/data');
      expect(stored!.loglevel).toBe(LogLevel.DEBUG);
    });

    it('should override existing values when the same key is saved', () => {
      saveUserOptions({ dataDirectory: '/old/path' });
      saveUserOptions({ dataDirectory: '/new/path' });

      const stored = getStoredOptions();
      expect(stored!.dataDirectory).toBe('/new/path');
    });

    it('should not clear existing options when saving empty config', () => {
      saveUserOptions({ dataDirectory: '/test/data', loglevel: LogLevel.DEBUG });
      saveUserOptions({});

      const stored = getStoredOptions();
      expect(stored!.dataDirectory).toBe('/test/data');
      expect(stored!.loglevel).toBe(LogLevel.DEBUG);
    });
  });

  describe('clearUserOptions', () => {
    it('should remove all options from localStorage', () => {
      saveUserOptions({ dataDirectory: '/test/data', loglevel: LogLevel.DEBUG });
      expect(localStorage.getItem(BACKEND_OPTIONS)).not.toBeNull();

      clearUserOptions();
      expect(localStorage.getItem(BACKEND_OPTIONS)).toBeNull();
    });

    it('should not throw when localStorage is already empty', () => {
      expect(localStorage.getItem(BACKEND_OPTIONS)).toBeNull();
      expect(() => clearUserOptions()).not.toThrow();
    });
  });

  describe('reset regression', () => {
    it('should not restore old values when saving empty config after clear', () => {
      saveUserOptions({ dataDirectory: '/custom/data' });
      expect(getStoredOptions()!.dataDirectory).toBe('/custom/data');

      clearUserOptions();
      expect(localStorage.getItem(BACKEND_OPTIONS)).toBeNull();

      // After clear, a subsequent saveUserOptions({}) must not bring back old values.
      // This is the exact scenario that caused the bug: resetOptions used to call
      // saveUserOptions({}) which merged {} with existing localStorage, preserving
      // the old dataDirectory.
      saveUserOptions({});
      const stored = getStoredOptions();
      expect(stored!.dataDirectory).toBeUndefined();
    });

    it('should allow saving new options after clear', () => {
      saveUserOptions({ dataDirectory: '/old/path' });
      clearUserOptions();

      saveUserOptions({ dataDirectory: '/new/path' });
      const stored = getStoredOptions();
      expect(stored!.dataDirectory).toBe('/new/path');
    });
  });

  describe('with file config', () => {
    beforeEach(() => {
      vi.mocked(useInterop().config).mockResolvedValue({
        logDirectory: '/Users/home/rotki/logs',
      });
    });

    it('should use default config', async () => {
      const loaded = vi.fn();
      let backendManagement: ReturnType<typeof useBackendManagement> | null = null;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement(loaded);
        },
      });

      await nextTick();
      await flushPromises();

      expect(backendManagement).not.toBeNull();
      const { options, defaultLogDirectory, fileConfig } = backendManagement!;

      expect(get(options)).toStrictEqual({
        logDirectory: '/Users/home/rotki/logs',
      });
      expect(get(fileConfig)).toStrictEqual({
        logDirectory: '/Users/home/rotki/logs',
      });

      expect(get(defaultLogDirectory)).toBe('/Users/home/rotki/logs');
      expect(loaded).toHaveBeenCalledOnce();
    });

    it('should get saved data in localStorage', async () => {
      const loaded = vi.fn();
      const savedOptions = {
        loglevel: LogLevel.CRITICAL,
        maxSizeInMbAllLogs: 10,
        sqliteInstructions: 100,
        maxLogfilesNum: 1000,
      };
      localStorage.setItem(BACKEND_OPTIONS, JSON.stringify(savedOptions));

      let backendManagement: ReturnType<typeof useBackendManagement> | null = null;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement(loaded);
        },
      });

      await nextTick();
      await flushPromises();

      expect(backendManagement).not.toBeNull();
      const { options } = backendManagement!;

      expect(get(options)).toStrictEqual({
        logDirectory: '/Users/home/rotki/logs',
        loglevel: LogLevel.CRITICAL,
        maxLogfilesNum: 1000,
        maxSizeInMbAllLogs: 10,
        sqliteInstructions: 100,
      });

      expect(loaded).toHaveBeenCalledOnce();
    });

    it('should restart backend session', async () => {
      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);

      const { resetSessionBackend } = backendManagement;

      await resetSessionBackend();

      expect(useInterop().restartBackend).toBeCalledWith({
        logDirectory: '/Users/home/rotki/logs',
      });
    });
  });

  describe('without file config', () => {
    beforeEach(() => {
      vi.mocked(useInterop().config).mockResolvedValue({});
    });

    it('should save options', async () => {
      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);
      const { saveOptions } = backendManagement;
      const newOptions = {
        logDirectory: 'new_log_directory',
        dataDirectory: 'new_data_directory',
      };

      await saveOptions(newOptions);

      const storageOptions = JSON.parse(localStorage.getItem(BACKEND_OPTIONS) || '');
      expect(storageOptions).toMatchObject(expect.objectContaining(newOptions));

      expect(useInterop().restartBackend).toBeCalledWith(expect.objectContaining(newOptions));
    });

    it('should reset options and clear localStorage', async () => {
      vi.mocked(useInterop().config).mockResolvedValue({});
      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);
      const { resetOptions } = backendManagement;

      await resetOptions();

      expect(localStorage.getItem(BACKEND_OPTIONS)).toBeNull();

      expect(useInterop().restartBackend).toBeCalledWith({});
    });

    it('should clear persisted options so they do not reappear after reset', async () => {
      localStorage.setItem(BACKEND_OPTIONS, JSON.stringify({ dataDirectory: '/custom/data' }));

      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);
      const { resetOptions } = backendManagement;

      await resetOptions();

      // After reset, localStorage must be fully cleared so that stale options
      // (like a custom dataDirectory) don't persist across sessions.
      expect(localStorage.getItem(BACKEND_OPTIONS)).toBeNull();
    });

    it('should not restart backend session', async () => {
      vi.mocked(getBackendUrl).mockReturnValue({
        sessionOnly: false,
        url: '',
      });
      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);
      const { resetSessionBackend } = backendManagement;

      await resetSessionBackend();

      expect(useInterop().restartBackend).not.toBeCalled();
    });

    it('should restart backend if the url is not set', async () => {
      const url = '';
      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);
      const { backendChanged } = backendManagement;

      await backendChanged(url);

      expect(useInterop().restartBackend).toBeCalled();
      expect(useMainStore().connect).toHaveBeenCalledWith(url);
    });

    it('should not backend if the url is set', async () => {
      const url = 'test_backend_url';
      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);
      const { backendChanged } = backendManagement;

      await backendChanged(url);

      expect(useInterop().restartBackend).not.toBeCalled();
      expect(useMainStore().connect).toHaveBeenCalledWith(url);
    });

    it('should not do anything on setupBackend, if connected=true', async () => {
      const store = useMainStore();
      store.connected = true;

      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);

      const { setupBackend } = backendManagement;

      await setupBackend();

      expect(useInterop().restartBackend).not.toBeCalled();
    });

    it('should restart backend, if connected=false and url is not set', async () => {
      const store = useMainStore();
      store.connected = false;

      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);
      const { setupBackend } = backendManagement;

      await setupBackend();

      expect(useInterop().restartBackend).toBeCalled();
      expect(store.connect).toHaveBeenCalledWith();
    });

    it('should not restart backend, if connected=false and url is set', async () => {
      const store = useMainStore();
      store.connected = false;

      const url = 'test_backend_url';

      vi.mocked(getBackendUrl).mockReturnValue({
        sessionOnly: false,
        url,
      });

      let backendManagement: ReturnType<typeof useBackendManagement> | undefined;

      mount({
        template: '<div/>',
        setup() {
          backendManagement = useBackendManagement();
        },
      });

      await nextTick();
      await flushPromises();

      assert(backendManagement);

      const { setupBackend } = backendManagement;

      await setupBackend();

      expect(useInterop().restartBackend).not.toBeCalled();
      expect(store.connect).toHaveBeenCalledWith(url);
    });
  });
});
