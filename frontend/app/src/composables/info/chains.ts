import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { type EvmChain } from '@rotki/common/lib/data';
import { type ChainInfo } from '@/types/api/chains';

export const useSupportedChains = createSharedComposable(() => {
  const { fetchSupportedChains } = useSupportedChainsApi();

  const supportedChains = asyncComputed(() => fetchSupportedChains(), [], {
    lazy: true
  });

  const evmChainsData: ComputedRef<ChainInfo[]> = computed(() => {
    return get(supportedChains).filter(
      x => x.type === 'evm' && !!x.evmChainName
    );
  });

  const evmChains: ComputedRef<string[]> = computed(() => {
    return get(evmChainsData).map(x => x.name!);
  });

  const evmChainNames: ComputedRef<EvmChain[]> = computed(() => {
    return get(evmChainsData).map(x => x.evmChainName!);
  });

  const isEvm = (chain: MaybeRef<Blockchain>) =>
    computed(() => {
      const blockchain = get(chain);
      return get(evmChains).includes(blockchain);
    });

  const getEvmChainName = (
    chain: MaybeRef<Blockchain>
  ): ComputedRef<EvmChain | null> =>
    computed(() => {
      return (
        get(evmChainsData).find(x => x.name === chain)?.evmChainName || null
      );
    });

  return {
    evmChains,
    evmChainNames,
    getEvmChainName,
    isEvm
  };
});
