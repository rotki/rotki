import { BackendCode } from '@shared/ipc';

export const useBackendMessagesStore = defineStore('backendMessages', () => {
  const startupErrorMessage = ref('');
  const isMacOsVersionUnsupported = ref(false);
  const isWinVersionUnsupported = ref(false);

  const isDevelopment = checkIfDevelopment();
  const { setupListeners } = useInterop();
  const { restartBackend } = useBackendManagement();
  const { t } = useI18n();
  const { start } = useMonitorStore();
  const { connect } = useMainStore();
  const { showAbout } = storeToRefs(useAreaVisibilityStore());
  const { logged } = storeToRefs(useSessionAuthStore());

  onBeforeMount(() => {
    setupListeners({
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
      onAbout: () => set(showAbout, true),
      onRestart: async () => {
        set(startupErrorMessage, '');
        await restartBackend();
      },
      onProcessDetected: (pids) => {
        set(
          startupErrorMessage,
          t('error.process_running', {
            pids: pids.join(', '),
          }).toString(),
        );
      },
    });

    connect();
    if (isDevelopment && get(logged))
      start();

    const search = window.location.search;
    const skipUpdate = search.includes('skip_update');
    if (skipUpdate)
      sessionStorage.setItem('skip_update', '1');
  });

  return {
    startupErrorMessage,
    isMacOsVersionUnsupported,
    isWinVersionUnsupported,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBackendMessagesStore, import.meta.hot));
