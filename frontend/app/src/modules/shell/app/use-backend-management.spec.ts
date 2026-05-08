import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import '@test/i18n';

const mockConnect = vi.fn();
const mockSetWsConnectionEnabled = vi.fn();
const mockRestartBackend = vi.fn();
const mockConfig = vi.fn();
const mockGetBackendUrl = vi.fn();

vi.mock('@/modules/shell/app/use-backend-connection', () => ({
  useBackendConnection: vi.fn(() => ({
    cancelConnectionAttempts: vi.fn(),
    connect: mockConnect,
    getInfo: vi.fn(),
    getVersion: vi.fn(),
    stopConnectionAttempts: vi.fn(),
  })),
}));

vi.mock('@/modules/shell/app/use-websocket-connection', () => ({
  useWebsocketConnection: vi.fn(() => ({
    connect: vi.fn(),
    connected: ref(false),
    disconnect: vi.fn(),
    setConnectionEnabled: mockSetWsConnectionEnabled,
  })),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => ({
    get isPackaged(): boolean {
      return true;
    },
    config: mockConfig,
    restartBackend: mockRestartBackend,
    setLogLevel: vi.fn(),
  })),
}));

vi.mock('@/modules/shell/app/backend-options', () => ({
  clearUserOptions: vi.fn(),
  loadUserOptions: vi.fn((): Record<string, unknown> => ({})),
  saveUserOptions: vi.fn(),
}));

vi.mock('@/modules/auth/account-management', () => ({
  deleteBackendUrl: vi.fn(),
  getBackendUrl: (): { url: string; sessionOnly: boolean } => mockGetBackendUrl(),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn((): string => 'WARNING'),
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
  setLevel: vi.fn(),
}));

describe('useBackendManagement', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    vi.clearAllMocks();
    mockConfig.mockResolvedValue({});
    mockRestartBackend.mockResolvedValue(true);
    mockGetBackendUrl.mockReturnValue({ sessionOnly: false, url: '' });
  });

  afterEach(() => {
    scope.stop();
    vi.clearAllMocks();
  });

  async function importModule(): Promise<typeof import('./use-backend-management')> {
    return import('./use-backend-management');
  }

  describe('restartBackend', () => {
    it('should re-enable connectionEnabled after restart when it was disabled by a prior termination error', async () => {
      const store = useMainStore();
      const { connectionEnabled } = storeToRefs(store);
      // simulate prior TERMINATED error having disabled connection attempts
      set(connectionEnabled, false);

      const { useBackendManagement } = await importModule();
      const { restartBackend } = scope.run(() => useBackendManagement())!;
      await restartBackend();

      expect(get(connectionEnabled)).toBe(true);
      expect(mockSetWsConnectionEnabled).toHaveBeenCalledWith(true);
      expect(mockConnect).toHaveBeenCalled();
    });

    it('should call interop.restartBackend before re-enabling and connecting', async () => {
      const callOrder: string[] = [];
      mockRestartBackend.mockImplementation(async (): Promise<boolean> => {
        callOrder.push('restart');
        return true;
      });
      mockSetWsConnectionEnabled.mockImplementation((): void => {
        callOrder.push('setWs');
      });
      mockConnect.mockImplementation((): void => {
        callOrder.push('connect');
      });

      const { useBackendManagement } = await importModule();
      const { restartBackend } = scope.run(() => useBackendManagement())!;
      await restartBackend();

      expect(callOrder).toEqual(['restart', 'setWs', 'connect']);
    });

    it('should leave connectionEnabled true when it was already true', async () => {
      const store = useMainStore();
      const { connectionEnabled } = storeToRefs(store);

      const { useBackendManagement } = await importModule();
      const { restartBackend } = scope.run(() => useBackendManagement())!;
      await restartBackend();

      expect(get(connectionEnabled)).toBe(true);
      expect(mockSetWsConnectionEnabled).toHaveBeenCalledWith(true);
    });

    it('should set connected to false during restart', async () => {
      const store = useMainStore();
      store.setConnected(true);

      const { useBackendManagement } = await importModule();
      const { restartBackend } = scope.run(() => useBackendManagement())!;
      await restartBackend();

      expect(get(store.connected)).toBe(false);
    });
  });

  describe('backendChanged', () => {
    it('should re-enable connections when restarting due to a null url', async () => {
      const store = useMainStore();
      const { connectionEnabled } = storeToRefs(store);
      set(connectionEnabled, false);

      const { useBackendManagement } = await importModule();
      const { backendChanged } = scope.run(() => useBackendManagement())!;
      await backendChanged(null);

      expect(get(connectionEnabled)).toBe(true);
      expect(mockSetWsConnectionEnabled).toHaveBeenCalledWith(true);
      expect(mockConnect).toHaveBeenCalled();
    });

    it('should connect to a custom url without restarting', async () => {
      const { useBackendManagement } = await importModule();
      const { backendChanged } = scope.run(() => useBackendManagement())!;
      await backendChanged('http://custom:4242');

      expect(mockRestartBackend).not.toHaveBeenCalled();
      expect(mockConnect).toHaveBeenCalledWith('http://custom:4242');
    });
  });
});
