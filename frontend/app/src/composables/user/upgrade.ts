import { Ref } from 'vue';

export const useUpgradeMessage = (loading: Ref<boolean>) => {
  const showUpgradeMessage = ref(false);

  const { start, stop } = useTimeoutFn(
    () => {
      set(showUpgradeMessage, true);
    },
    15000,
    {
      immediate: false
    }
  );

  watch(loading, loading => {
    if (loading) {
      start();
    } else {
      stop();
      set(showUpgradeMessage, false);
    }
  });

  return {
    showUpgradeMessage
  };
};
