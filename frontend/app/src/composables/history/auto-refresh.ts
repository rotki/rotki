export function useHistoryAutoRefresh(refresh: () => Promise<void>): void {
  const { refreshPeriod } = storeToRefs(useFrontendSettingsStore());
  const period = computed(() => get(refreshPeriod) * 60 * 1000);

  const { pause, resume, isActive } = useIntervalFn(() => startPromise(refresh()), period, {
    immediate: false,
  });

  onBeforeMount(() => {
    if (get(period) > 0)
      resume();
  });

  onUnmounted(() => {
    if (isActive)
      pause();
  });
}
