import type { Ref } from 'vue';
import { BackendCode, type DebugStateGroup, type OAuthResult } from '@shared/ipc';
import { checkIfDevelopment, startPromise } from '@shared/utils';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { api } from '@/modules/core/api';
import { logger } from '@/modules/core/common/logging/logging';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { setMcpServerState } from '@/modules/settings/backend/use-mcp-server-state';
import { resetDebugState } from '@/modules/shell/app/debug-state-reset';
import { useAppQuitting } from '@/modules/shell/app/use-app-quitting';
import { useBackendConnection } from '@/modules/shell/app/use-backend-connection';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useMonitorService } from './use-monitor-service';
import { useWebsocketConnection } from './use-websocket-connection';

type OAuthCallback = (oAuthResult: OAuthResult) => void;

interface UseBackendMessagesInternalReturn {
  isMacOsVersionUnsupported: Readonly<Ref<boolean>>;
  isWinVersionUnsupported: Readonly<Ref<boolean>>;
  registerOAuthCallbackHandler: (handler: OAuthCallback) => void;
  startupErrorMessage: Readonly<Ref<string>>;
  unregisterOAuthCallbackHandler: (handler: OAuthCallback) => void;
}

function useBackendMessagesInternal(): UseBackendMessagesInternalReturn {
  const startupErrorMessage = shallowRef<string>('');
  const isMacOsVersionUnsupported = shallowRef<boolean>(false);
  const isWinVersionUnsupported = shallowRef<boolean>(false);

  const isDevelopment = checkIfDevelopment();
  const { getStartupError, setDataDirectory, setupListeners } = useInterop();
  const { restartBackend } = useBackendManagement();
  const { start: startMonitoring, stop: stopMonitoring } = useMonitorService();
  const { showAbout } = storeToRefs(useAreaVisibilityStore());
  const { logged } = storeToRefs(useSessionAuthStore());

  const oauthCallbackHandlers = ref<Array<OAuthCallback>>([]);
  const { setConnectionEnabled: setWsConnectionEnabled } = useWebsocketConnection();
  const { stopConnectionAttempts } = useBackendConnection();
  const { connected, connectionEnabled } = storeToRefs(useMainStore());
  const { startQuitting } = useAppQuitting();

  /**
   * Halts all outbound activity against the backend: stops the connection ping
   * loop and disables future attempts, stops all monitoring (periodic tasks,
   * websocket, etc.), and disables websocket reconnection. Used whenever the
   * backend is unavailable or about to become unavailable.
   */
  function haltBackendActivity(): void {
    stopConnectionAttempts();
    stopMonitoring();
    setWsConnectionEnabled(false);
  }

  /**
   * Handle a startup error by logging it and updating the appropriate state.
   * Also stops all monitoring, connection attempts, and WebSocket connections since the backend is unavailable.
   */
  function handleStartupError(message: string, code: BackendCode): void {
    logger.error(message, code);
    haltBackendActivity();

    if (code === BackendCode.TERMINATED) {
      set(startupErrorMessage, message);
    }
    else if (code === BackendCode.MACOS_VERSION) {
      set(isMacOsVersionUnsupported, true);
    }
    else if (code === BackendCode.WIN_VERSION) {
      set(isWinVersionUnsupported, true);
    }
  }

  function registerOAuthCallbackHandler(handler: OAuthCallback): void {
    const handlers = get(oauthCallbackHandlers);
    set(oauthCallbackHandlers, [...handlers, handler]);
  }

  function unregisterOAuthCallbackHandler(handler: OAuthCallback): void {
    const handlers = get(oauthCallbackHandlers);
    const index = handlers.indexOf(handler);
    if (index !== -1) {
      const newHandlers = [...handlers];
      newHandlers.splice(index, 1);
      set(oauthCallbackHandlers, newHandlers);
    }
  }

  /**
   * Disarm the data directory menu entry as soon as the backend goes away, so a
   * restart into a different directory cannot leave the old one clickable. The
   * arming half lives in `getInfo`, which is where the directory becomes known.
   */
  watch(connected, (isConnected) => {
    if (!isConnected)
      setDataDirectory('');
  });

  onBeforeMount(() => {
    // 1. First, synchronously check for any startup error that occurred before mount.
    // This guarantees we don't miss errors that happened before the Vue app was ready.
    const pendingError = getStartupError();
    if (pendingError) {
      handleStartupError(pendingError.message, pendingError.code);
    }

    // 2. Set up listeners for future async errors and other IPC messages.
    // This also signals to the main process that the renderer is ready.
    setupListeners({
      onAbout: () => set(showAbout, true),
      onError: (message: string, code: BackendCode) => {
        handleStartupError(message, code);
      },
      onMcpState: setMcpServerState,
      onOAuthCallback: (oAuthResult: OAuthResult) => {
        const handlers = get(oauthCallbackHandlers);
        handlers.forEach((handler) => {
          handler(oAuthResult);
        });
      },
      /**
       * Tears the app down for a quit the main process has already decided on.
       *
       * @remarks
       * The order is load-bearing: `startQuitting` swaps the UI for the shutdown screen,
       * which unmounts the notification popup. Halting activity or stopping requests before
       * that lets requests unwinding against the dying backend surface errors over a window
       * that is on its way out.
       */
      onAppClosing: () => {
        startQuitting();
        haltBackendActivity();
        api.stopRequests();
      },
      onResetDebugState: (group: DebugStateGroup) => {
        // Storage-backed refs hold their value in memory, so a wipe only shows after a reload.
        if (resetDebugState(group).length > 0)
          window.location.reload();
      },
      onRestart: () => {
        set(startupErrorMessage, '');
        // Re-enable connections for the restart attempt
        set(connectionEnabled, true);
        setWsConnectionEnabled(true);
        startPromise(restartBackend());
      },
    });

    if (isDevelopment && get(logged))
      startMonitoring();
  });

  return {
    isMacOsVersionUnsupported: readonly(isMacOsVersionUnsupported),
    isWinVersionUnsupported: readonly(isWinVersionUnsupported),
    registerOAuthCallbackHandler,
    startupErrorMessage: readonly(startupErrorMessage),
    unregisterOAuthCallbackHandler,
  };
}

export const useBackendMessages = createGlobalState(useBackendMessagesInternal);
