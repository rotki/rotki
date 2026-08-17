import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { createMock } from '@test/utils/create-mock';
import { withSetup } from '@test/utils/with-setup';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import '@test/i18n';

const mockConnect = vi.fn();
const mockSetWsConnectionEnabled = vi.fn();
const mockRestartBackend = vi.fn();
const mockConfig = vi.fn();
const mockGetBackendUrl = vi.fn();
const mockControlProbe = vi.fn();
const mockControlRestart = vi.fn();
/** Flipped per test: `false` is the docker/web build, where the app owns no backend process. */
let packaged = true;

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
  useInterop: vi.fn(() => createMock<ReturnType<typeof useInterop>>({
    get isPackaged(): boolean {
      return packaged;
    },
    config: mockConfig,
    restartBackend: mockRestartBackend,
    setLogLevel: vi.fn(),
  })),
}));

vi.mock('@/modules/core/control/use-control', () => ({
  useControl: vi.fn(() => ({
    available: ref(true),
    probe: mockControlProbe,
    restart: mockControlRestart,
    serviceInfo: vi.fn(),
    setServiceAutostart: vi.fn(),
    setServiceRunning: vi.fn(),
    supportsOptions: false,
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
  let wrapper: ReturnType<typeof withSetup>['wrapper'] | undefined;

  function create(composable: typeof import('./use-backend-management').useBackendManagement): ReturnType<typeof composable> {
    const setup = withSetup(() => composable());
    wrapper = setup.wrapper;
    return setup.result;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockConfig.mockResolvedValue({});
    mockRestartBackend.mockResolvedValue(true);
    mockGetBackendUrl.mockReturnValue({ sessionOnly: false, url: '' });
    packaged = true;
    mockControlProbe.mockResolvedValue(true);
    mockControlRestart.mockResolvedValue(undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
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
      const { restartBackend } = create(useBackendManagement);
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
      const { restartBackend } = create(useBackendManagement);
      await restartBackend();

      expect(callOrder).toEqual(['restart', 'setWs', 'connect']);
    });

    it('should leave connectionEnabled true when it was already true', async () => {
      const store = useMainStore();
      const { connectionEnabled } = storeToRefs(store);

      const { useBackendManagement } = await importModule();
      const { restartBackend } = create(useBackendManagement);
      await restartBackend();

      expect(get(connectionEnabled)).toBe(true);
      expect(mockSetWsConnectionEnabled).toHaveBeenCalledWith(true);
    });

    it('should set connected to false during restart', async () => {
      const store = useMainStore();
      store.setConnected(true);

      const { useBackendManagement } = await importModule();
      const { restartBackend } = create(useBackendManagement);
      await restartBackend();

      expect(get(store.connected)).toBe(false);
    });
  });

  describe('forceRestart intent', () => {
    it('should attach (forceRestart=false) when setupBackend runs on a page refresh', async () => {
      const { useBackendManagement } = await importModule();
      const { setupBackend } = create(useBackendManagement);
      await setupBackend();

      expect(mockRestartBackend).toHaveBeenCalledWith(expect.anything(), false);
    });

    it('should force a restart when applying changed user options', async () => {
      const config = { dataDirectory: '/tmp/rotki-data' };
      const { useBackendManagement } = await importModule();
      const { applyUserOptions } = create(useBackendManagement);
      await applyUserOptions(config, false);

      expect(mockRestartBackend).toHaveBeenCalledWith(config, true);
    });

    it('should force a restart when resetting options', async () => {
      const { useBackendManagement } = await importModule();
      const { resetOptions } = create(useBackendManagement);
      await resetOptions();

      expect(mockRestartBackend).toHaveBeenCalledWith(expect.anything(), true);
    });
  });

  describe('backendChanged', () => {
    it('should re-enable connections when restarting due to a null url', async () => {
      const store = useMainStore();
      const { connectionEnabled } = storeToRefs(store);
      set(connectionEnabled, false);

      const { useBackendManagement } = await importModule();
      const { backendChanged } = create(useBackendManagement);
      await backendChanged(null);

      expect(get(connectionEnabled)).toBe(true);
      expect(mockSetWsConnectionEnabled).toHaveBeenCalledWith(true);
      expect(mockConnect).toHaveBeenCalled();
    });

    it('should connect to a custom url without restarting', async () => {
      const { useBackendManagement } = await importModule();
      const { backendChanged } = create(useBackendManagement);
      await backendChanged('http://custom:4242');

      expect(mockRestartBackend).not.toHaveBeenCalled();
      expect(mockConnect).toHaveBeenCalledWith('http://custom:4242');
    });
  });

  describe('docker control', () => {
    it('should not restart the backend while merely setting up at boot', async () => {
      // Regression: with the electron-only guard removed from restartBackend,
      // setupBackend's boot path started issuing a real /_control restart, so
      // docker bounced its whole backend tree on every page load - and before
      // login the endpoint refuses, which stranded the user short of the login
      // screen because setupBackend rejected before reaching connect().
      packaged = false;

      const { useBackendManagement } = await importModule();
      const { setupBackend } = create(useBackendManagement);
      await setupBackend();

      expect(mockControlRestart).not.toHaveBeenCalled();
      expect(mockConnect).toHaveBeenCalled();
    });

    it('should restart through the control endpoint when asked explicitly', async () => {
      packaged = false;

      const { useBackendManagement } = await importModule();
      const { restartBackend } = create(useBackendManagement);
      await restartBackend();

      expect(mockControlRestart).toHaveBeenCalledOnce();
      expect(mockRestartBackend).not.toHaveBeenCalled();
      expect(mockConnect).toHaveBeenCalled();
    });

    it('should stay a no-op where no control endpoint is served', async () => {
      // The plain web build: probing says no, so the old behaviour stands.
      packaged = false;
      mockControlProbe.mockResolvedValue(false);

      const { useBackendManagement } = await importModule();
      const { restartBackend } = create(useBackendManagement);
      await restartBackend();

      expect(mockControlRestart).not.toHaveBeenCalled();
    });
  });
});
