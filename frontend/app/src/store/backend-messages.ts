import { useBackendManagement } from '@/composables/backend';
import { useInterop } from '@/composables/electron-interop';
import { useMonitorStore } from '@/store/monitor';
import { useSessionAuthStore } from '@/store/session/auth';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { logger } from '@/utils/logging';
import { BackendCode } from '@shared/ipc';
import { checkIfDevelopment, startPromise } from '@shared/utils';

export const useBackendMessagesStore = defineStore('backendMessages', () => {
  const startupErrorMessage = ref('');
  const isMacOsVersionUnsupported = ref(false);
  const isWinVersionUnsupported = ref(false);

  const isDevelopment = checkIfDevelopment();
  const { setupListeners } = useInterop();
  const { restartBackend } = useBackendManagement();
  const { t } = useI18n({ useScope: 'global' });
  const { start } = useMonitorStore();
  const { showAbout } = storeToRefs(useAreaVisibilityStore());
  const { logged } = storeToRefs(useSessionAuthStore());

  onBeforeMount(() => {
    setupListeners({
      onAbout: () => set(showAbout, true),
      onError: (backendOutput: string | Error, code: BackendCode) => {
        logger.error(backendOutput, code);
        if (code === BackendCode.TERMINATED) {
          const message = typeof backendOutput === 'string' ? backendOutput : backendOutput.message;
          set(startupErrorMessage, message);
        }
        else if (code === BackendCode.MACOS_VERSION) {
          set(isMacOsVersionUnsupported, true);
        }
        else if (code === BackendCode.WIN_VERSION) {
          set(isWinVersionUnsupported, true);
        }
      },
      onProcessDetected: (pids) => {
        set(
          startupErrorMessage,
          t('error.process_running', {
            pids: pids.join(', '),
          }),
        );
      },
      onRestart: () => {
        set(startupErrorMessage, '');
        startPromise(restartBackend());
      },
    });

    if (isDevelopment && get(logged))
      start();
  });

  return {
    isMacOsVersionUnsupported,
    isWinVersionUnsupported,
    startupErrorMessage,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBackendMessagesStore, import.meta.hot));
