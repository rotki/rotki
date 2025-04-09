import type {
  ChainInfo,
  EvmChainEntries,
  EvmChainInfo,
  EvmLikeChainInfo,
  SubstrateChainInfo,
  SupportedChains,
} from '@/types/api/chains';
import type { MaybeRef } from '@vueuse/core';
import { useSupportedChainsApi } from '@/composables/api/info/chains';
import { useArrayInclude } from '@/composables/array';
import { Routes } from '@/router/routes';
import { useMainStore } from '@/store/main';
import { isBlockchain } from '@/types/blockchain/chains';
import { Blockchain, getTextToken, toHumanReadable, toSentenceCase, toSnakeCase } from '@rotki/common';

function isEvmChain(info: ChainInfo): info is EvmChainInfo {
  return info.type === 'evm';
}

function isSubstrateChain(info: ChainInfo): info is SubstrateChainInfo {
  return info.type === 'substrate';
}

function isEvmLikeChain(info: ChainInfo): info is EvmLikeChainInfo {
  return info.type === 'evmlike';
}

export const useSupportedChains = createSharedComposable(() => {
  const { fetchAllEvmChains, fetchSupportedChains } = useSupportedChainsApi();

  const { connected } = toRefs(useMainStore());

  const supportedChains = asyncComputed<SupportedChains>(async () => {
    if (get(connected))
      return fetchSupportedChains();

    return [];
  }, []);

  const allEvmChains = asyncComputed<EvmChainEntries>(async () => {
    if (get(connected))
      return fetchAllEvmChains();

    return [];
  }, []);

  const evmChainsData = computed<EvmChainInfo[]>(() =>
    // isEvmChain guard does not work the same with useArrayFilter
    get(supportedChains).filter(isEvmChain),
  );

  const substrateChainsData = computed<SubstrateChainInfo[]>(() =>
    get(supportedChains).filter(isSubstrateChain),
  );

  const evmLikeChainsData = computed<EvmLikeChainInfo[]>(() =>
    get(supportedChains).filter(isEvmLikeChain),
  );

  const txEvmChains: ComputedRef<EvmChainInfo[]> = useArrayFilter(evmChainsData, x => x.id !== Blockchain.AVAX);

  const txChains = computed<ChainInfo[]>(() => [...get(txEvmChains), ...get(evmLikeChainsData)]);

  const evmChains: ComputedRef<string[]> = useArrayMap(evmChainsData, x => x.id);

  const evmChainNames: ComputedRef<string[]> = useArrayMap(evmChainsData, x => x.evmChainName);

  const isEvm = (chain: MaybeRef<string>): ComputedRef<boolean> => useArrayInclude(evmChains, chain);

  const supportsTransactions = (chain: MaybeRef<string>): boolean => {
    const chains = get(txEvmChains);
    const selectedChain = get(chain);
    return chains.some(x => x.id === selectedChain);
  };

  const isEvmLikeChains = (chain: MaybeRef<string>): boolean => {
    const chains = get(evmLikeChainsData);
    const selectedChain = get(chain);
    return chains.some(x => x.id === selectedChain);
  };

  const getEvmChainName = (chain: string): string | undefined =>
    get(evmChainsData).find(x => x.id === chain)?.evmChainName || undefined;

  const getChainInfoByName = (chain: MaybeRef<string>): ComputedRef<ChainInfo | null> =>
    computed(() => get(supportedChains).find(({ name }) => name.toLowerCase() === get(chain).toLowerCase()) || null);

  const getChainInfoById = (chain: MaybeRef<string>): ComputedRef<ChainInfo | null> =>
    computed(() => get(supportedChains).find(x => x.id === get(chain)) || null);

  const getNativeAsset = (chain: MaybeRef<string>): string => {
    const blockchain = get(chain);
    return (
      [...get(evmChainsData), ...get(substrateChainsData), ...get(evmLikeChainsData)].find(
        ({ id }) => id === blockchain,
      )?.nativeToken || blockchain.toUpperCase()
    );
  };

  /**
   *
   * @param {string} location - String to find the chain (can be the chain id, or the evmChainName)
   * @return {Blockchain} - Blockchain id found
   * @example
   * getChain('zksync_lite'); // Blockchain.ZKSYNC_LITE
   * getChain('ethereum'); // Blockchain.ETH
   */
  const matchChain = (location: string): Blockchain | undefined => {
    // note: we're using toSnakeCase here to always ensure that chains
    // with combined names gets parsed to match their chain name
    const chainData = get(supportedChains).find((item) => {
      const transformed = getTextToken(toSnakeCase(location));
      if ('evmChainName' in item && getTextToken(item.evmChainName) === transformed)
        return true;

      return getTextToken(item.id) === transformed;
    });

    if (chainData && isBlockchain(chainData.id))
      return chainData.id;
    return undefined;
  };

  /**
   * Retrieves the blockchain chain based on the specified location.
   *
   * This function attempts to match a given location to a specific blockchain
   * chain using the `matchChain` function.
   * If no match is found, the provided default value is returned.
   * The default value defaults to `Blockchain.ETH` if not explicitly specified.
   *
   * @param {string} location - The location used to determine the blockchain chain.
   * @param {Blockchain} [defaultValue=Blockchain.ETH] - The blockchain chain to return if no match is found.
   * @returns {Blockchain} The blockchain chain corresponding to the specified location or the default value.
   */
  const getChain = (
    location: string,
    defaultValue: Blockchain = Blockchain.ETH,
  ): Blockchain => matchChain(location) ?? defaultValue;

  /**
   *
   * @param {string} location - String to find the chain (can be the chain id, or the evmChainName)
   * @return {string} - Readable chain name
   * @example
   * getChainName('zksync_lite'); // ZKSync Lite
   * getChainName('ethereum'); // Ethereum
   */
  const getChainName = (location: MaybeRef<string>): ComputedRef<string> =>
    computed(() => {
      const locationVal = get(location);
      const chain = matchChain(locationVal);
      if (!chain)
        return toSentenceCase(locationVal);

      return get(getChainInfoById(chain))?.name || toSentenceCase(locationVal);
    });

  const getChainImageUrl = (chain: MaybeRef<string>): ComputedRef<string> => computed<string>(() => {
    const chainVal = get(chain);
    const image = get(getChainInfoById(chainVal))?.image || `${chainVal}.svg`;

    return `./assets/images/protocols/${image}`;
  });

  const txChainsToLocation = useArrayMap(txChains, (item) => {
    if ('evmChainName' in item)
      return toHumanReadable(item.evmChainName);

    return toHumanReadable(item.id);
  });

  const getChainAccountType = (chain: string): string | undefined => {
    const allChains = get(supportedChains);
    const match = allChains.find(entry => entry.id === chain);
    if (match?.type === 'evmlike')
      return 'evm';
    return match?.type;
  };

  const getBlockchainRedirectLink = (blockchain: string): string => {
    const chain = get(blockchain);
    if (chain === Blockchain.ETH2) {
      return '/staking/eth2';
    }

    const target = getChainAccountType(chain) ?? 'evm';
    return `${Routes.ACCOUNTS.toString()}/${target}`;
  };

  return {
    allEvmChains,
    evmChainNames,
    evmChains,
    evmChainsData,
    evmLikeChainsData,
    getBlockchainRedirectLink,
    getChain,
    getChainAccountType,
    getChainImageUrl,
    getChainInfoById,
    getChainInfoByName,
    getChainName,
    getEvmChainName,
    getNativeAsset,
    isEvm,
    isEvmLikeChains,
    matchChain,
    supportedChains,
    supportsTransactions,
    txChains,
    txChainsToLocation,
    txEvmChains,
  };
});
