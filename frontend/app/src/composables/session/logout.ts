export function useSessionStateCleaner() {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { uploadStatus } = useSync();
  const { start, stop } = useMonitorStore();

  watch(logged, (logged, wasLogged) => {
    if (logged) {
      if (!wasLogged)
        start();

      return;
    }
    set(uploadStatus, null);
    stop();
    resetState();
  });
}
