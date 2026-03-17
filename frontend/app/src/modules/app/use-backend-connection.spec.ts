import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/store/main';
import '@test/i18n';

const mockInfo = vi.fn();
const mockPing = vi.fn();

vi.mock('@/composables/api/info', () => ({
  useInfoApi: vi.fn(() => ({
    info: mockInfo,
    ping: mockPing,
  })),
}));

vi.mock('@/modules/api/rotki-api', () => ({
  api: {
    setup: vi.fn(),
  },
}));

vi.mock('@/modules/api/api-urls', () => ({
  apiUrls: { coreApiUrl: 'http://localhost:4242', colibriApiUrl: 'http://localhost:4343' },
  defaultApiUrls: { coreApiUrl: 'http://localhost:4242', colibriApiUrl: 'http://localhost:4343' },
}));

vi.mock('@/utils/logging', () => ({
  getDefaultLogLevel: vi.fn((): string => 'WARNING'),
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
  setLevel: vi.fn(),
}));

vi.mock('@shared/utils', () => ({
  startPromise: vi.fn((p: Promise<unknown>): void => { p.catch(() => {}); }),
}));

describe('useBackendConnection', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  async function importModule(): Promise<typeof import('./use-backend-connection')> {
    return import('./use-backend-connection');
  }

  describe('getVersion', () => {
    it('should update store version from backend info', async () => {
      mockInfo.mockResolvedValue({
        version: {
          downloadUrl: 'https://example.com/download',
          latestVersion: '2.0.0',
          ourVersion: '1.5.0',
        },
      });

      const { useBackendConnection } = await importModule();
      const { getVersion } = scope.run(() => useBackendConnection())!;
      await getVersion();

      const store = useMainStore();
      expect(get(store.version)).toEqual({
        downloadUrl: 'https://example.com/download',
        latestVersion: '2.0.0',
        version: '1.5.0',
      });
    });

    it('should not update version when info returns no version', async () => {
      mockInfo.mockResolvedValue({});

      const { useBackendConnection } = await importModule();
      const { getVersion } = scope.run(() => useBackendConnection())!;
      await getVersion();

      const store = useMainStore();
      expect(get(store.version).version).toBe('');
    });
  });

  describe('getInfo', () => {
    it('should update store with backend info', async () => {
      mockInfo.mockResolvedValue({
        acceptDockerRisk: true,
        backendDefaultArguments: { maxLogfilesNum: 5, maxSizeInMbAllLogs: 300, sqliteInstructions: 1000 },
        dataDirectory: '/data',
        logLevel: 'DEBUG',
      });

      const { useBackendConnection } = await importModule();
      const { getInfo } = scope.run(() => useBackendConnection())!;
      await getInfo();

      const store = useMainStore();
      expect(get(store.dataDirectory)).toBe('/data');
      expect(get(store.logLevel)).toBe('DEBUG');
      expect(get(store.dockerRiskAccepted)).toBe(true);
    });
  });

  describe('connect', () => {
    it('should skip connection when connectionEnabled is false', async () => {
      const store = useMainStore();
      const { connectionEnabled } = storeToRefs(store);
      set(connectionEnabled, false);

      const { useBackendConnection } = await importModule();
      const { connect } = scope.run(() => useBackendConnection())!;
      connect();

      vi.advanceTimersByTime(5000);
      expect(mockPing).not.toHaveBeenCalled();
    });

    it('should set connectionFailure after 20 failed attempts', async () => {
      const store = useMainStore();
      mockPing.mockRejectedValue(new Error('timeout'));

      const { useBackendConnection } = await importModule();
      const { connect } = scope.run(() => useBackendConnection())!;
      connect();

      for (let i = 0; i <= 20; i++) {
        vi.advanceTimersByTime(2000);
        await vi.runAllTimersAsync();
      }

      expect(get(store.connectionFailure)).toBe(true);
    });
  });

  describe('cancelConnectionAttempts', () => {
    it('should cancel ongoing connection interval', async () => {
      mockPing.mockRejectedValue(new Error('timeout'));

      const { useBackendConnection } = await importModule();
      const { cancelConnectionAttempts, connect } = scope.run(() => useBackendConnection())!;
      connect();

      vi.advanceTimersByTime(2000);
      await vi.runAllTimersAsync();
      const callCount = mockPing.mock.calls.length;

      cancelConnectionAttempts();

      vi.advanceTimersByTime(10000);
      await vi.runAllTimersAsync();
      expect(mockPing.mock.calls).toHaveLength(callCount);
    });
  });

  describe('stopConnectionAttempts', () => {
    it('should disable connection and cancel attempts', async () => {
      const store = useMainStore();

      const { useBackendConnection } = await importModule();
      const { stopConnectionAttempts } = scope.run(() => useBackendConnection())!;
      stopConnectionAttempts();

      expect(get(store.connectionEnabled)).toBe(false);
    });
  });
});
