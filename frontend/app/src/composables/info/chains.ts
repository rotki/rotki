import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { type ChainInfo, type EvmChainInfo } from '@/types/api/chains';

const isEvmChain = (info: ChainInfo): info is EvmChainInfo => {
  return info.type === 'evm';
};

export const useSupportedChains = createSharedComposable(() => {
  const { fetchSupportedChains } = useSupportedChainsApi();

  const supportedChains = asyncComputed(() => fetchSupportedChains(), [], {
    lazy: true
  });

  const evmChainsData: ComputedRef<EvmChainInfo[]> = computed(() => {
    // isEvmChain guard does not work the same with useArrayFilter
    return get(supportedChains).filter(isEvmChain);
  });

  const txEvmChains: ComputedRef<EvmChainInfo[]> = useArrayFilter(
    evmChainsData,
    x => x.name !== 'AVAX'
  );

  const evmChains: ComputedRef<string[]> = useArrayMap(
    evmChainsData,
    x => x.name
  );

  const evmChainNames: ComputedRef<string[]> = useArrayMap(
    evmChainsData,
    x => x.evmChainName
  );

  const isEvm = (chain: MaybeRef<Blockchain>) =>
    useArrayInclude(evmChains, chain);

  const supportsTransactions = (chain: MaybeRef<Blockchain>): boolean => {
    const chains = get(txEvmChains);
    const selectedChain = get(chain);
    return chains.some(x => x.name === selectedChain);
  };

  const getEvmChainName = (chain: Blockchain): string | null =>
    get(evmChainsData).find(x => x.name === chain)?.evmChainName || null;

  return {
    evmChains,
    evmChainNames,
    txEvmChains,
    getEvmChainName,
    isEvm,
    supportsTransactions
  };
});
