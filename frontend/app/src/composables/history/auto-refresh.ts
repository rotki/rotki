export const useHistoryAutoRefresh = (refresh: () => Promise<void>) => {
  const { refreshPeriod } = storeToRefs(useFrontendSettingsStore());
  const period = computed(() => get(refreshPeriod) * 60 * 1000);

  const { pause, resume, isActive } = useIntervalFn(refresh, period, {
    immediate: false
  });

  onBeforeMount(async () => {
    if (get(period) > 0) {
      resume();
    }
  });

  onUnmounted(() => {
    if (isActive) {
      pause();
    }
  });
};
