import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { BackendCode, type DebugStateGroup, type Listeners, type OAuthResult, type StartupError } from '@shared/ipc';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useMainStore } from '@/modules/core/common/use-main-store';

type BackendMessages = ReturnType<typeof import('./use-backend-messages').useBackendMessages>;

const getStartupError = vi.fn<() => StartupError | null>(() => null);
const setDataDirectory = vi.fn<(dataDirectory: string) => void>();
const setupListeners = vi.fn<(listeners: Listeners) => void>();
const restartBackend = vi.fn<() => Promise<void>>(async () => {});
const startMonitoring = vi.fn<() => void>();
const stopMonitoring = vi.fn<() => void>();
const setWsConnectionEnabled = vi.fn<(enabled: boolean) => void>();
const stopConnectionAttempts = vi.fn<() => void>();
const startQuitting = vi.fn<() => void>();
const stopRequests = vi.fn<() => void>();
const setMcpServerState = vi.fn<(state: unknown) => void>();
const resetDebugState = vi.fn<(group: DebugStateGroup) => string[]>(() => []);
const reload = vi.fn<() => void>();

const development = ref<boolean>(false);

vi.mock('@shared/utils', async importOriginal => ({
  ...await importOriginal<typeof import('@shared/utils')>(),
  checkIfDevelopment: (): boolean => get(development),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): ReturnType<typeof useInterop> => createMock<ReturnType<typeof useInterop>>({
    getStartupError,
    setDataDirectory,
    setupListeners,
  }),
}));

vi.mock('@/modules/shell/app/use-backend-management', () => ({
  useBackendManagement: (): { restartBackend: typeof restartBackend } => ({ restartBackend }),
}));

vi.mock('@/modules/shell/app/use-monitor-service', () => ({
  useMonitorService: (): { start: typeof startMonitoring; stop: typeof stopMonitoring } => ({
    start: startMonitoring,
    stop: stopMonitoring,
  }),
}));

vi.mock('@/modules/shell/app/use-websocket-connection', () => ({
  useWebsocketConnection: (): { setConnectionEnabled: typeof setWsConnectionEnabled } => ({
    setConnectionEnabled: setWsConnectionEnabled,
  }),
}));

vi.mock('@/modules/shell/app/use-backend-connection', () => ({
  useBackendConnection: (): { stopConnectionAttempts: typeof stopConnectionAttempts } => ({
    stopConnectionAttempts,
  }),
}));

vi.mock('@/modules/shell/app/use-app-quitting', () => ({
  useAppQuitting: (): { startQuitting: typeof startQuitting } => ({ startQuitting }),
}));

vi.mock('@/modules/settings/backend/use-mcp-server-state', () => ({ setMcpServerState }));

vi.mock('@/modules/shell/app/debug-state-reset', () => ({ resetDebugState }));

vi.mock('@/modules/core/api', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/api')>(),
  api: { stopRequests },
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
  setLevel: vi.fn(),
}));

const wrappers: VueWrapper[] = [];

async function mountHost(): Promise<BackendMessages> {
  vi.doUnmock('@/modules/shell/app/use-backend-messages');
  vi.resetModules();
  const { useBackendMessages } = await import('./use-backend-messages');

  let captured: BackendMessages | undefined;
  let setupError: Error | undefined;
  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      try {
        captured = useBackendMessages();
      }
      catch (error) {
        setupError = error instanceof Error ? error : new Error(String(error));
      }
      return (): ReturnType<typeof h> => h('div');
    },
  });

  wrappers.push(mount(Host));
  if (setupError)
    throw setupError;
  return captured!;
}

function listeners(): Listeners {
  expect(setupListeners).toHaveBeenCalledOnce();
  return setupListeners.mock.calls[0][0];
}

function oAuthSuccess(service: string): OAuthResult {
  return { accessToken: 'token', service, success: true };
}

describe('modules/shell/app/useBackendMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getStartupError.mockReturnValue(null);
    resetDebugState.mockReturnValue([]);
    set(development, false);
    vi.stubGlobal('location', { reload });
    setActivePinia(createCustomPinia());
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
    vi.unstubAllGlobals();
  });

  describe('an error that happened before the app mounted', () => {
    it('should surface a terminated backend as the startup message', async () => {
      getStartupError.mockReturnValue({ code: BackendCode.TERMINATED, message: 'backend died' });

      const { isMacOsVersionUnsupported, isWinVersionUnsupported, startupErrorMessage } = await mountHost();

      expect(get(startupErrorMessage)).toBe('backend died');
      expect(get(isMacOsVersionUnsupported)).toBe(false);
      expect(get(isWinVersionUnsupported)).toBe(false);
    });

    it('should flag an unsupported macos without also showing the raw message', async () => {
      getStartupError.mockReturnValue({ code: BackendCode.MACOS_VERSION, message: 'too old' });

      const { isMacOsVersionUnsupported, startupErrorMessage } = await mountHost();

      expect(get(isMacOsVersionUnsupported)).toBe(true);
      expect(get(startupErrorMessage)).toBe('');
    });

    it('should flag an unsupported windows without also showing the raw message', async () => {
      getStartupError.mockReturnValue({ code: BackendCode.WIN_VERSION, message: 'too old' });

      const { isWinVersionUnsupported, startupErrorMessage } = await mountHost();

      expect(get(isWinVersionUnsupported)).toBe(true);
      expect(get(startupErrorMessage)).toBe('');
    });

    it('should still halt the backend for a code it does not recognise, showing nothing', async () => {
      getStartupError.mockReturnValue({ code: 99, message: 'something new' });

      const { isMacOsVersionUnsupported, isWinVersionUnsupported, startupErrorMessage } = await mountHost();

      expect(stopConnectionAttempts).toHaveBeenCalledOnce();
      expect(get(startupErrorMessage)).toBe('');
      expect(get(isMacOsVersionUnsupported)).toBe(false);
      expect(get(isWinVersionUnsupported)).toBe(false);
    });

    it('should halt every outbound channel, not just the one that failed', async () => {
      getStartupError.mockReturnValue({ code: BackendCode.TERMINATED, message: 'backend died' });

      await mountHost();

      expect(stopConnectionAttempts).toHaveBeenCalledOnce();
      expect(stopMonitoring).toHaveBeenCalledOnce();
      expect(setWsConnectionEnabled).toHaveBeenCalledWith(false);
    });

    it('should leave the app untouched when the backend started cleanly', async () => {
      const { isMacOsVersionUnsupported, isWinVersionUnsupported, startupErrorMessage } = await mountHost();

      expect(get(startupErrorMessage)).toBe('');
      expect(get(isMacOsVersionUnsupported)).toBe(false);
      expect(get(isWinVersionUnsupported)).toBe(false);
      expect(stopConnectionAttempts).not.toHaveBeenCalled();
      expect(stopMonitoring).not.toHaveBeenCalled();
      expect(setWsConnectionEnabled).not.toHaveBeenCalled();
    });

    it('should read the pending error before registering the listeners that would report a later one', async () => {
      await mountHost();

      expect(getStartupError.mock.invocationCallOrder[0])
        .toBeLessThan(setupListeners.mock.invocationCallOrder[0]);
    });
  });

  describe('an error reported after the app mounted', () => {
    it('should handle a late error exactly as one pending at mount', async () => {
      const { startupErrorMessage } = await mountHost();

      listeners().onError('backend died later', BackendCode.TERMINATED);

      expect(get(startupErrorMessage)).toBe('backend died later');
      expect(stopConnectionAttempts).toHaveBeenCalledOnce();
      expect(stopMonitoring).toHaveBeenCalledOnce();
      expect(setWsConnectionEnabled).toHaveBeenCalledWith(false);
    });
  });

  describe('the quit sequence', () => {
    it('should show the shutdown screen before anything can error against the dying backend', async () => {
      await mountHost();

      listeners().onAppClosing?.();

      const [quitting] = startQuitting.mock.invocationCallOrder;
      expect(quitting).toBeLessThan(stopConnectionAttempts.mock.invocationCallOrder[0]);
      expect(quitting).toBeLessThan(stopMonitoring.mock.invocationCallOrder[0]);
      expect(quitting).toBeLessThan(stopRequests.mock.invocationCallOrder[0]);
    });

    it('should stop in-flight requests once the backend is no longer being talked to', async () => {
      await mountHost();

      listeners().onAppClosing?.();

      expect(stopRequests).toHaveBeenCalledOnce();
      expect(stopRequests.mock.invocationCallOrder[0])
        .toBeGreaterThan(setWsConnectionEnabled.mock.invocationCallOrder[0]);
    });
  });

  describe('a debug state reset', () => {
    it('should reload so the wiped keys stop being served from memory', async () => {
      resetDebugState.mockReturnValue(['rotki.first_run']);
      await mountHost();

      listeners().onResetDebugState?.('firstRun');

      expect(reload).toHaveBeenCalledOnce();
    });

    it('should not reload when the group cleared nothing', async () => {
      await mountHost();

      listeners().onResetDebugState?.('firstRun');

      expect(resetDebugState).toHaveBeenCalledWith('firstRun');
      expect(reload).not.toHaveBeenCalled();
    });
  });

  describe('a restart', () => {
    it('should clear the error and re-arm both connections before asking for the restart', async () => {
      getStartupError.mockReturnValue({ code: BackendCode.TERMINATED, message: 'backend died' });
      const { startupErrorMessage } = await mountHost();
      const { connectionEnabled } = storeToRefs(useMainStore());
      set(connectionEnabled, false);

      listeners().onRestart();

      expect(get(startupErrorMessage)).toBe('');
      expect(get(connectionEnabled)).toBe(true);
      expect(setWsConnectionEnabled).toHaveBeenLastCalledWith(true);
      expect(restartBackend).toHaveBeenCalledOnce();
    });
  });

  describe('the menu-driven messages', () => {
    it('should open the about dialog', async () => {
      await mountHost();
      const { showAbout } = storeToRefs(useAreaVisibilityStore());

      listeners().onAbout();

      expect(get(showAbout)).toBe(true);
    });

    it('should forward an mcp server state straight through', async () => {
      await mountHost();

      listeners().onMcpState?.('Ready');

      expect(setMcpServerState).toHaveBeenCalledWith('Ready');
    });
  });

  describe('the oauth callback handlers', () => {
    it('should fan a result out to every registered handler', async () => {
      const { registerOAuthCallbackHandler } = await mountHost();
      const first = vi.fn();
      const second = vi.fn();
      registerOAuthCallbackHandler(first);
      registerOAuthCallbackHandler(second);

      listeners().onOAuthCallback?.(oAuthSuccess('google'));

      expect(first).toHaveBeenCalledWith(oAuthSuccess('google'));
      expect(second).toHaveBeenCalledWith(oAuthSuccess('google'));
    });

    it('should stop calling a handler that unregistered, and keep calling the rest', async () => {
      const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = await mountHost();
      const leaving = vi.fn();
      const staying = vi.fn();
      registerOAuthCallbackHandler(leaving);
      registerOAuthCallbackHandler(staying);

      unregisterOAuthCallbackHandler(leaving);
      listeners().onOAuthCallback?.(oAuthSuccess('monerium'));

      expect(leaving).not.toHaveBeenCalled();
      expect(staying).toHaveBeenCalledOnce();
    });

    it('should ignore an unregister for a handler that was never registered', async () => {
      const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = await mountHost();
      const registered = vi.fn();
      registerOAuthCallbackHandler(registered);

      unregisterOAuthCallbackHandler(vi.fn());
      listeners().onOAuthCallback?.(oAuthSuccess('google'));

      expect(registered).toHaveBeenCalledOnce();
    });

    it('should drop only one registration when the same handler registered twice', async () => {
      const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = await mountHost();
      const twice = vi.fn();
      registerOAuthCallbackHandler(twice);
      registerOAuthCallbackHandler(twice);

      unregisterOAuthCallbackHandler(twice);
      listeners().onOAuthCallback?.(oAuthSuccess('google'));

      expect(twice).toHaveBeenCalledOnce();
    });

    it('should reach a handler registered after the callback was already delivered once', async () => {
      const { registerOAuthCallbackHandler } = await mountHost();
      const late = vi.fn();

      listeners().onOAuthCallback?.(oAuthSuccess('google'));
      registerOAuthCallbackHandler(late);
      listeners().onOAuthCallback?.(oAuthSuccess('monerium'));

      expect(late).toHaveBeenCalledExactlyOnceWith(oAuthSuccess('monerium'));
    });
  });

  describe('the data directory menu entry', () => {
    it('should disarm it when the backend goes away', async () => {
      await mountHost();
      const { setConnected } = useMainStore();

      setConnected(true);
      await nextTick();
      expect(setDataDirectory).not.toHaveBeenCalled();

      setConnected(false);
      await nextTick();

      expect(setDataDirectory).toHaveBeenCalledExactlyOnceWith('');
    });

    it('should leave it alone when the backend connects', async () => {
      await mountHost();
      const { setConnected } = useMainStore();

      setConnected(true);
      await nextTick();

      expect(setDataDirectory).not.toHaveBeenCalled();
    });
  });

  describe('the development-only monitoring', () => {
    it('should start monitoring when a development build mounts logged in', async () => {
      set(development, true);
      setActivePinia(createCustomPinia());
      set(storeToRefs(useSessionAuthStore()).logged, true);

      await mountHost();

      expect(startMonitoring).toHaveBeenCalledOnce();
    });

    it('should not start monitoring in a production build', async () => {
      set(storeToRefs(useSessionAuthStore()).logged, true);

      await mountHost();

      expect(startMonitoring).not.toHaveBeenCalled();
    });

    it('should not start monitoring before anyone has logged in', async () => {
      set(development, true);

      await mountHost();

      expect(startMonitoring).not.toHaveBeenCalled();
    });
  });
});
