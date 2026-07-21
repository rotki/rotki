import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAccountCategoryHelperReturn {
  isEvm: ComputedRef<boolean>;
  chainIds: ComputedRef<string[]>;
}

export function useAccountCategoryHelper(category: MaybeRefOrGetter<string>): UseAccountCategoryHelperReturn {
  const { supportedChains } = useSupportedChains();

  const isEvm = computed<boolean>(() => toValue(category) === 'evm');

  const chainIds = computed<string[]>(() => {
    const categoryVal = toValue(category);

    return get(supportedChains)
      .filter(item => item.type === categoryVal || (categoryVal === 'evm' && item.type === 'evmlike'))
      .map(chain => chain.id);
  });

  return {
    chainIds,
    isEvm,
  };
}
