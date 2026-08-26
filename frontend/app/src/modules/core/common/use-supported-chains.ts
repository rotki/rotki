import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { Blockchain, getTextToken, toHumanReadable, toSnakeCase } from '@rotki/common';
import {
  type ChainInfo,
  ChainType,
  type EvmChainEntries,
  type EvmChainInfo,
  type EvmLikeChainInfo,
  type SupportedChains,
} from '@/modules/core/api/types/chains';
import { isBlockchain } from '@/modules/core/common/chains';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { useSupportedChainsApi } from '@/modules/core/common/use-supported-chains-api';
import { useSupportedChainsStore } from '@/modules/core/common/use-supported-chains-store';

/**
 * Chains whose protocol decoding coverage is still limited. The backend does
 * not expose a maturity flag, so the set is maintained here until it does.
 */
const EARLY_INTEGRATION_CHAINS: ReadonlySet<string> = new Set(['avax', 'hyperliquid', 'monad', 'sonic']);

function isEvmChain(info: ChainInfo): info is EvmChainInfo {
  return info.type === ChainType.EVM;
}

function isEvmLikeChain(info: ChainInfo): info is EvmLikeChainInfo {
  return info.type === ChainType.EVMLIKE;
}

function isBitcoinChain(info: ChainInfo): boolean {
  return info.type === ChainType.BITCOIN;
}

function isSolanaChain(info: ChainInfo): boolean {
  return info.type === ChainType.SOLANA;
}

interface UseSupportedChainsReturn {
  allEvmChains: Readonly<Ref<EvmChainEntries>>;
  allTxChainsInfo: ComputedRef<ChainInfo[]>;
  bitcoinChainsData: ComputedRef<ChainInfo[]>;
  decodableTxChainsInfo: ComputedRef<ChainInfo[]>;
  evmAndEvmLikeTxChainsInfo: ComputedRef<ChainInfo[]>;
  evmChains: ComputedRef<string[]>;
  evmChainsData: ComputedRef<EvmChainInfo[]>;
  evmLikeChainsData: ComputedRef<EvmLikeChainInfo[]>;
  getBlockchainRedirectLink: (blockchain: string) => string;
  getChain: (location: string, defaultValue?: Blockchain) => Blockchain;
  getChainAccountType: (chain: string) => string | undefined;
  getChainImageUrl: (chain: string) => string;
  getChainName: (location: string) => string;
  getEvmChainId: (name: string) => number | undefined;
  getEvmChainName: (chain: string) => string | undefined;
  getNativeAsset: (chain: string) => string;
  isBtcChains: (chain: string) => boolean;
  isDecodableChains: (chain: string) => boolean;
  isEarlyIntegrationChain: (chain: string) => boolean;
  isEvm: (chain: string) => boolean;
  isEvmCompatible: (chain: string) => boolean;
  isEvmLikeChains: (chain: string) => boolean;
  isSolanaChains: (chain: string) => boolean;
  matchChain: (location: string) => Blockchain | undefined;
  solanaChainsData: ComputedRef<ChainInfo[]>;
  supportedChains: Readonly<Ref<SupportedChains>>;
  supportsTransactions: (chain: string) => boolean;
  txChainsToLocation: ComputedRef<string[]>;
  txEvmChains: ComputedRef<EvmChainInfo[]>;
  useBlockchainRedirectLink: (blockchain: MaybeRefOrGetter<string>) => ComputedRef<string>;
  useChainImageUrl: (chain: MaybeRefOrGetter<string>) => ComputedRef<string>;
  useChainName: (location: MaybeRefOrGetter<string | undefined>) => ComputedRef<string>;
  refreshSupportedChains: () => Promise<void>;
}

export const useSupportedChains = createSharedComposable((): UseSupportedChainsReturn => {
  const { fetchAllEvmChains, fetchSupportedChains } = useSupportedChainsApi();

  const { allEvmChains, supportedChains } = storeToRefs(useSupportedChainsStore());

  const evmChainsData = computed<EvmChainInfo[]>(() =>
    get(supportedChains).filter(isEvmChain),
  );

  const evmLikeChainsData = computed<EvmLikeChainInfo[]>(() =>
    get(supportedChains).filter(isEvmLikeChain),
  );

  const bitcoinChainsData = computed<ChainInfo[]>(() =>
    get(supportedChains).filter(isBitcoinChain),
  );

  const solanaChainsData = computed<ChainInfo[]>(() =>
    get(supportedChains).filter(isSolanaChain),
  );

  const txEvmChains = computed<EvmChainInfo[]>(() =>
    get(evmChainsData).filter(x => x.id !== Blockchain.AVAX),
  );

  const evmAndEvmLikeTxChainsInfo = computed<ChainInfo[]>(() => [
    ...get(txEvmChains),
    ...get(evmLikeChainsData),
  ]);

  const decodableTxChainsInfo = computed<ChainInfo[]>(() => [
    ...get(evmAndEvmLikeTxChainsInfo),
    ...get(solanaChainsData),
  ]);

  const allTxChainsInfo = computed<ChainInfo[]>(() => [
    ...get(decodableTxChainsInfo),
    ...get(bitcoinChainsData),
  ]);

  const evmChains = computed<string[]>(() => get(evmChainsData).map(x => x.id));

  // Lookup structures for O(1) access
  const chainById = computed<Map<string, ChainInfo>>(() => {
    const map = new Map<string, ChainInfo>();
    for (const chain of get(supportedChains))
      map.set(chain.id, chain);
    return map;
  });

  const evmChainSet = computed<Set<string>>(() => new Set(get(evmChains)));
  const evmLikeChainSet = computed<Set<string>>(() => new Set(get(evmLikeChainsData).map(x => x.id)));
  const btcChainSet = computed<Set<string>>(() => new Set(get(bitcoinChainsData).map(x => x.id)));
  const solanaChainSet = computed<Set<string>>(() => new Set(get(solanaChainsData).map(x => x.id)));
  const decodableChainSet = computed<Set<string>>(() => new Set(get(decodableTxChainsInfo).map(x => x.id)));
  const txEvmChainSet = computed<Set<string>>(() => new Set(get(txEvmChains).map(x => x.id)));

  const chainTokenLookup = computed<Map<string, Blockchain>>(() => {
    const map = new Map<string, Blockchain>();
    for (const item of get(supportedChains)) {
      if (!isBlockchain(item.id))
        continue;
      map.set(getTextToken(item.id), item.id);
      map.set(getTextToken(item.name), item.id);
      if (isEvmChain(item))
        map.set(getTextToken(item.evmChainName), item.id);
    }
    return map;
  });

  const isEvm = (chain: string): boolean => get(evmChainSet).has(chain);

  const supportsTransactions = (chain: string): boolean => get(txEvmChainSet).has(chain);

  const isEvmLikeChains = (chain: string): boolean => get(evmLikeChainSet).has(chain);

  const isEvmCompatible = (chain: string): boolean =>
    isEvm(chain) || isEvmLikeChains(chain);

  const isBtcChains = (chain: string): boolean => get(btcChainSet).has(chain);

  const isSolanaChains = (chain: string): boolean => get(solanaChainSet).has(chain);

  const isEarlyIntegrationChain = (chain: string): boolean => EARLY_INTEGRATION_CHAINS.has(chain);

  const isDecodableChains = (chain: string): boolean => get(decodableChainSet).has(chain);

  // Info lookup (internal)
  const getChainInfoById = (chain: string): ChainInfo | null =>
    get(chainById).get(chain) ?? null;

  const getEvmChainName = (chain: string): string | undefined => {
    const info = getChainInfoById(chain);
    return info && isEvmChain(info) ? info.evmChainName : undefined;
  };

  const getNativeAsset = (chain: string): string => {
    const info = getChainInfoById(chain);
    return (info && 'nativeToken' in info ? info.nativeToken : undefined) ?? chain.toUpperCase();
  };

  const getEvmChainId = (name: string): number | undefined =>
    get(allEvmChains).find(x => x.name === name)?.id;

  /**
   * Resolves a chain identifier to its {@link Blockchain}.
   *
   * @param location - a chain id or an evmChainName
   * @returns the matching chain, or `undefined` when nothing matches; prefer this over
   * {@link getChain}, which substitutes Ethereum instead
   * @example
   * ```ts
   * matchChain('zksync_lite'); // Blockchain.ZKSYNC_LITE
   * matchChain('ethereum');    // Blockchain.ETH
   * ```
   */
  const matchChain = (location: string): Blockchain | undefined =>
    get(chainTokenLookup).get(getTextToken(toSnakeCase(location)));

  /**
   * {@link matchChain} with a fallback instead of `undefined`.
   *
   * @remarks
   * The default answers Ethereum for anything unrecognised, which silently files an unknown
   * chain's data under ETH. Reach for {@link matchChain} wherever "no match" needs handling.
   *
   * @param location - a chain id or an evmChainName
   * @param defaultValue - returned when nothing matches
   * @defaultValue `Blockchain.ETH`
   */
  const getChain = (
    location: string,
    defaultValue: Blockchain = Blockchain.ETH,
  ): Blockchain => matchChain(location) ?? defaultValue;

  /**
   * The human-readable display name for a chain.
   *
   * @param location - a chain id or an evmChainName
   * @example
   * ```ts
   * getChainName('zksync_lite'); // ZKSync Lite
   * getChainName('ethereum');    // Ethereum
   * ```
   */
  const useChainName = (location: MaybeRefOrGetter<string | undefined>): ComputedRef<string> =>
    computed(() => {
      const locationVal = toValue(location);
      if (!locationVal)
        return '';

      const chain = matchChain(locationVal);
      if (!chain)
        return toHumanReadable(locationVal, 'capitalize');

      return getChainInfoById(chain)?.name ?? toHumanReadable(locationVal, 'capitalize');
    });

  const getChainName = (location: string): string => {
    const chain = matchChain(location);
    if (!chain)
      return toHumanReadable(location, 'capitalize');

    return getChainInfoById(chain)?.name ?? toHumanReadable(location, 'capitalize');
  };

  const useChainImageUrl = (chain: MaybeRefOrGetter<string>): ComputedRef<string> => computed<string>(() => {
    const chainVal = toValue(chain);
    const image = getChainInfoById(chainVal)?.image ?? `${chainVal}.svg`;

    return getPublicProtocolImagePath(image);
  });

  const getChainImageUrl = (chain: string): string => {
    const image = getChainInfoById(chain)?.image ?? `${chain}.svg`;
    return getPublicProtocolImagePath(image);
  };

  const txChainsToLocation = computed<string[]>(() =>
    get(evmAndEvmLikeTxChainsInfo).map((item) => {
      if (isEvmChain(item))
        return toHumanReadable(item.evmChainName);

      return toHumanReadable(item.id);
    }),
  );

  const getChainAccountType = (chain: string): string | undefined => {
    const match = getChainInfoById(chain);
    if (match?.type === ChainType.EVMLIKE)
      return ChainType.EVM;
    return match?.type;
  };

  const getBlockchainRedirectLink = (blockchain: string): string => {
    if (blockchain === Blockchain.ETH2)
      return '/staking/eth2';

    const target = getChainAccountType(blockchain) ?? ChainType.EVM;
    const basePath = `/accounts/${target}`;
    if (target === ChainType.EVM)
      return `${basePath}/accounts?chain=${blockchain}`;

    return `${basePath}?chain=${blockchain}`;
  };

  const useBlockchainRedirectLink = (blockchain: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed<string>(() => getBlockchainRedirectLink(toValue(blockchain)));

  // Loaded imperatively from the unlock flow (post-login), so the calls never fire
  // on the login screen. The store state is cleared on logout by `resetState()`.
  const refreshSupportedChains = async (): Promise<void> => {
    const [chains, evmChains] = await Promise.all([
      fetchSupportedChains(),
      fetchAllEvmChains(),
    ]);
    set(supportedChains, chains);
    set(allEvmChains, evmChains);
  };

  return {
    allEvmChains,
    allTxChainsInfo,
    bitcoinChainsData,
    decodableTxChainsInfo,
    evmAndEvmLikeTxChainsInfo,
    evmChains,
    evmChainsData,
    evmLikeChainsData,
    getBlockchainRedirectLink,
    getChain,
    getChainAccountType,
    getChainImageUrl,
    getChainName,
    getEvmChainId,
    getEvmChainName,
    getNativeAsset,
    isBtcChains,
    isDecodableChains,
    isEarlyIntegrationChain,
    isEvm,
    isEvmCompatible,
    isEvmLikeChains,
    isSolanaChains,
    matchChain,
    refreshSupportedChains,
    solanaChainsData,
    supportedChains,
    supportsTransactions,
    txChainsToLocation,
    txEvmChains,
    useBlockchainRedirectLink,
    useChainImageUrl,
    useChainName,
  };
});
