import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useSupportedChains } from '@/composables/info/chains';

interface UseBlockchainAccountLoadingReturn {
  isEvm: ComputedRef<boolean>;
  chainIds: ComputedRef<string[]>;
}

export function useAccountCategoryHelper(category: MaybeRef<string>): UseBlockchainAccountLoadingReturn {
  const { supportedChains } = useSupportedChains();

  const isEvm = computed(() => get(category) === 'evm');

  const chainIds = computed<string[]>(() => {
    const categoryVal = get(category);

    return get(supportedChains)
      .filter(item => item.type === categoryVal || (categoryVal === 'evm' && item.type === 'evmlike'))
      .map(chain => chain.id);
  });

  return {
    chainIds,
    isEvm,
  };
}
