import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef, type Ref } from 'vue';
import {
  type ChainInfo,
  type EvmChainEntries,
  type EvmChainInfo,
  type SupportedChains
} from '@/types/api/chains';
import { isBlockchain } from '@/types/blockchain/chains';

const isEvmChain = (info: ChainInfo): info is EvmChainInfo =>
  info.type === 'evm';

export const useSupportedChains = createSharedComposable(() => {
  const { fetchSupportedChains, fetchAllEvmChains } = useSupportedChainsApi();

  const { connected } = toRefs(useMainStore());

  const supportedChains: Ref<SupportedChains> = asyncComputed<SupportedChains>(
    () => {
      if (get(connected)) {
        return fetchSupportedChains();
      }
      return [];
    },
    [],
    {
      lazy: true
    }
  );

  const allEvmChains: Ref<EvmChainEntries> = asyncComputed<EvmChainEntries>(
    () => {
      if (get(connected)) {
        return fetchAllEvmChains();
      }
      return [];
    },
    [],
    {
      lazy: true
    }
  );

  const evmChainsData: ComputedRef<EvmChainInfo[]> = computed(() =>
    // isEvmChain guard does not work the same with useArrayFilter
    get(supportedChains).filter(isEvmChain)
  );

  const txEvmChains: ComputedRef<EvmChainInfo[]> = useArrayFilter(
    evmChainsData,
    x => x.id !== 'AVAX'
  );

  const evmChains: ComputedRef<string[]> = useArrayMap(
    evmChainsData,
    x => x.id
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
    return chains.some(x => x.id === selectedChain);
  };

  const getEvmChainName = (chain: Blockchain): string | null =>
    get(evmChainsData).find(x => x.id === chain)?.evmChainName || null;

  const getChainInfoById = (
    chain: MaybeRef<Blockchain>
  ): ComputedRef<ChainInfo | null> =>
    computed(() => get(supportedChains).find(x => x.id === get(chain)) || null);

  const getNativeAsset = (chain: MaybeRef<Blockchain>) => {
    const blockchain = get(chain);
    return (
      get(evmChainsData).find(({ id }) => id === blockchain)?.nativeAsset ||
      blockchain
    );
  };

  const getChain = (evmChain: string): Blockchain => {
    const chainData = get(txEvmChains).find(
      ({ evmChainName }) => evmChainName === evmChain
    );
    if (chainData && isBlockchain(chainData.id)) {
      return chainData.id;
    }
    return Blockchain.ETH;
  };

  return {
    allEvmChains,
    supportedChains,
    evmChains,
    evmChainNames,
    txEvmChains,
    getNativeAsset,
    getEvmChainName,
    getChain,
    getChainInfoById,
    isEvm,
    supportsTransactions
  };
});
