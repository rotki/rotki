export function useSessionStateCleaner(): void {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { clearUploadStatus } = useSync();
  const { start, stop } = useMonitorStore();

  watch(logged, (logged, wasLogged) => {
    if (logged) {
      if (!wasLogged)
        start();

      return;
    }
    clearUploadStatus();
    stop();
    resetState();
  });
}
