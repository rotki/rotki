import { BackendCode, type OAuthResult } from '@shared/ipc';
import { checkIfDevelopment, startPromise } from '@shared/utils';
import { useBackendManagement } from '@/composables/backend';
import { useInterop } from '@/composables/electron-interop';
import { useMainStore } from '@/store/main';
import { useMonitorStore } from '@/store/monitor';
import { useSessionAuthStore } from '@/store/session/auth';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useWebsocketStore } from '@/store/websocket';
import { logger } from '@/utils/logging';

type OAuthCallback = (oAuthResult: OAuthResult) => void;

export const useBackendMessagesStore = defineStore('backendMessages', () => {
  const startupErrorMessage = ref('');
  const isMacOsVersionUnsupported = ref(false);
  const isWinVersionUnsupported = ref(false);

  const isDevelopment = checkIfDevelopment();
  const { getStartupError, setupListeners } = useInterop();
  const { restartBackend } = useBackendManagement();
  const { t } = useI18n({ useScope: 'global' });
  const { start: startMonitoring, stop: stopMonitoring } = useMonitorStore();
  const { showAbout } = storeToRefs(useAreaVisibilityStore());
  const { logged } = storeToRefs(useSessionAuthStore());

  const oauthCallbackHandlers = ref<Array<OAuthCallback>>([]);
  const { setConnectionEnabled: setWsConnectionEnabled } = useWebsocketStore();
  const { setConnectionEnabled: setMainConnectionEnabled, stopConnectionAttempts } = useMainStore();

  /**
   * Handle a startup error by logging it and updating the appropriate state.
   * Also stops all monitoring, connection attempts, and WebSocket connections since the backend is unavailable.
   */
  function handleStartupError(message: string, code: BackendCode): void {
    logger.error(message, code);
    // Stop connection ping loop and disable future connection attempts
    stopConnectionAttempts();
    // Stop all monitoring (periodic tasks, websocket, etc.) - backend is not available
    stopMonitoring();
    // Also explicitly disable websocket reconnection
    setWsConnectionEnabled(false);

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
      onOAuthCallback: (oAuthResult: OAuthResult) => {
        const handlers = get(oauthCallbackHandlers);
        handlers.forEach((handler) => {
          handler(oAuthResult);
        });
      },
      onProcessDetected: (pids) => {
        // Stop all connection attempts and monitoring - another backend process is running
        stopConnectionAttempts();
        stopMonitoring();
        setWsConnectionEnabled(false);
        set(
          startupErrorMessage,
          t('error.process_running', {
            pids: pids.join(', '),
          }),
        );
      },
      onRestart: () => {
        set(startupErrorMessage, '');
        // Re-enable connections for the restart attempt
        setMainConnectionEnabled(true);
        setWsConnectionEnabled(true);
        startPromise(restartBackend());
      },
    });

    if (isDevelopment && get(logged))
      startMonitoring();
  });

  return {
    isMacOsVersionUnsupported,
    isWinVersionUnsupported,
    registerOAuthCallbackHandler,
    startupErrorMessage,
    unregisterOAuthCallbackHandler,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBackendMessagesStore, import.meta.hot));
