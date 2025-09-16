import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';

interface AccountBalancesLifecycleOptions {
  category: MaybeRef<string>;
  fetchData: () => Promise<void>;
}

interface AccountBalancesLifecycleReturn {
  isDetectingTokens: Ref<boolean>;
  isSectionLoading: Ref<boolean>;
  operationRunning: Ref<boolean>;
  refreshDisabled: ComputedRef<boolean>;
}

export function useAccountBalancesLifecycle(options: AccountBalancesLifecycleOptions): AccountBalancesLifecycleReturn {
  const { category, fetchData } = options;

  const { isDetectingTokens, isSectionLoading, operationRunning } = useBlockchainAccountLoading(category);

  watchDebounced(
    logicOr(isDetectingTokens, isSectionLoading, operationRunning),
    async (isLoading, wasLoading) => {
      if (!isLoading && wasLoading)
        await fetchData();
    },
    {
      debounce: 800,
    },
  );

  onMounted(async () => {
    await fetchData();
  });

  return {
    isDetectingTokens,
    isSectionLoading,
    operationRunning,
    refreshDisabled: computed(() => get(isDetectingTokens) || get(isSectionLoading) || get(operationRunning)),
  };
}
