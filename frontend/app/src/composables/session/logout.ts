export const useSessionStateCleaner = () => {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { start, stop } = useMonitorStore();

  watch(logged, (logged, wasLogged) => {
    if (logged) {
      if (!wasLogged) {
        start();
      }
      return;
    }
    stop();
    resetState();
  });
};
