import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type {
  AddressBookEntry,
  AddressBookSimplePayload,
  AddressNameRequestPayload,
} from '@/modules/accounts/address-book/eth-names';
import { Blockchain, isValidAddress, isValidBchAddress, isValidBtcAddress, isValidEthAddress, isValidSolanaAddress } from '@rotki/common';
import { useAddressNamesStore } from '@/modules/accounts/address-book/use-address-names-store';
import { useAddressesNamesApi } from '@/modules/accounts/address-book/use-addresses-names-api';
import { isBlockchain } from '@/modules/core/common/chains';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { logger } from '@/modules/core/common/logging/logging';
import { createItemCache } from '@/modules/core/common/use-item-cache';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';

interface UseAddressNameResolutionReturn {
  getAddressName: (address: string, blockchain?: string) => string | undefined;
  getAddressNameSource: (address: string, blockchain?: string) => string | undefined;
  isAddressNamePending: (address: string, blockchain?: string) => boolean;
  getEnsName: (address: string) => string | null;
  useEnsNamesList: () => ComputedRef<string[]>;
  resetAddressNamesData: (items: AddressBookSimplePayload[]) => void;
  resetAddressesNames: () => void;
  refreshAvatarTimestamp: () => void;
  updateEnsNamesAndReset: (newResult: Record<string, string | null>) => void;
  useAddressInfo: <T extends keyof AddressBookEntry>(
    address: MaybeRefOrGetter<string>,
    field: T,
    blockchain?: MaybeRefOrGetter<string>,
  ) => ComputedRef<AddressBookEntry[T] | undefined>;
  useAddressName: (
    address: MaybeRefOrGetter<string>,
    blockchain?: MaybeRefOrGetter<string>,
  ) => ComputedRef<string | undefined>;
  useAddressNameSource: (
    address: MaybeRefOrGetter<string>,
    blockchain?: MaybeRefOrGetter<string>,
  ) => ComputedRef<string | undefined>;
  useAddressesWithoutNames: (blockchain?: MaybeRefOrGetter<string | null>) => ComputedRef<string[]>;
  useEnsAvatarUrl: (address: MaybeRefOrGetter<string>) => ComputedRef<string | null>;
}

export const useAddressNameResolution = createSharedComposable((): UseAddressNameResolutionReturn => {
  const enableAliasNames = useSetting('enableAliasNames');
  const store = useAddressNamesStore();
  const { addressNameStorage } = store;
  const { ensNames } = storeToRefs(store);
  const lastRefreshedAvatar = shallowRef<number>(Date.now());
  const { supportedChains } = useSupportedChains();
  const { ensAvatarUrl, getAddressesNames } = useAddressesNamesApi();

  const evmChainIds = computed<string[]>(() =>
    get(supportedChains)
      .filter(chain => chain.type === 'evm' || chain.type === 'evmlike')
      .map(chain => chain.id),
  );

  const solanaChainIds = computed<string[]>(() =>
    get(supportedChains)
      .filter(chain => chain.type === 'solana')
      .map(chain => chain.id),
  );

  const bitcoinChainIds = computed<string[]>(() =>
    get(supportedChains)
      .filter(chain => chain.type === 'bitcoin')
      .map(chain => chain.id),
  );

  const allChainIds = computed<string[]>(() =>
    get(supportedChains).map(chain => chain.id),
  );

  function getEnsName(address: string): string | null {
    if (!get(enableAliasNames))
      return null;

    return get(ensNames)[address] ?? null;
  }

  const ensNamesList = computed<string[]>(
    () => Object.values(get(ensNames)).filter((value): value is string => !!value),
  );

  const useEnsNamesList = (): ComputedRef<string[]> => ensNamesList;

  const useEnsAvatarUrl = (address: MaybeRefOrGetter<string>): ComputedRef<string | null> => computed<string | null>(() => {
    const ens = getEnsName(toValue(address));
    if (!ens)
      return null;

    return ensAvatarUrl(ens, get(lastRefreshedAvatar));
  });

  const createKey = (address: string, chain: string): string => `${address}#${chain}`;

  function isAddressResolvable(address: string, chain: string): boolean {
    if (get(evmChainIds).includes(chain))
      return isValidEthAddress(address);

    if (get(solanaChainIds).includes(chain))
      return isValidSolanaAddress(address);

    if (get(bitcoinChainIds).includes(chain))
      return isValidBtcAddress(address) || isValidBchAddress(address);

    return isValidAddress(address);
  }

  const fetchAddressesNames = async (keys: string[]) => {
    const payload: AddressNameRequestPayload[] = [];
    for (const key of keys) {
      const [address, blockchain] = key.split('#');
      if (isBlockchain(blockchain) && isAddressResolvable(address, blockchain))
        payload.push({ address, blockchain });
    }

    let result: AddressBookEntry[];
    if (payload.length > 0) {
      try {
        result = await getAddressesNames(payload);
      }
      catch (error: unknown) {
        logger.error(error);
        result = [];
      }
    }
    else {
      result = [];
    }

    const resultMap = new Map<string, AddressBookEntry>();
    for (const entry of result) resultMap.set(createKey(entry.address, entry.blockchain ?? ''), entry);

    return function* (): Generator<{ key: string; item: AddressBookEntry | undefined }, void> {
      for (const key of keys) {
        yield { item: resultMap.get(key), key };
      }
    };
  };

  const {
    getIsPending,
    refresh,
    reset: resetAddressesNames,
    resolve,
    unknown,
  } = createItemCache<AddressBookEntry | undefined>(async keys => fetchAddressesNames(keys), {
    label: 'address-name',
    maxSize: 5000,
    size: 500,
    storage: addressNameStorage,
  });

  function resolveAddressInfo<T extends keyof AddressBookEntry>(
    address: string,
    field: T,
    blockchain: string,
  ): AddressBookEntry[T] | undefined {
    if (!get(enableAliasNames) || !address)
      return undefined;

    if (!isBlockchain(blockchain) || blockchain === Blockchain.ETH2)
      return undefined;

    const key = createKey(address, blockchain);
    const cachedInfo = resolve(key);

    if (getIsPending(key) && !cachedInfo)
      return undefined;

    return cachedInfo?.[field] ?? undefined;
  }

  const useAddressInfo = <T extends keyof AddressBookEntry>(
    address: MaybeRefOrGetter<string>,
    field: T,
    blockchain: MaybeRefOrGetter<string> = Blockchain.ETH,
  ): ComputedRef<AddressBookEntry[T] | undefined> => computed<AddressBookEntry[T] | undefined>(
    () => resolveAddressInfo(toValue(address), field, toValue(blockchain)),
  );

  const useAddressName = (
    address: MaybeRefOrGetter<string>,
    blockchain: MaybeRefOrGetter<string> = Blockchain.ETH,
  ): ComputedRef<string | undefined> => useAddressInfo(address, 'name', blockchain);

  const useAddressNameSource = (
    address: MaybeRefOrGetter<string>,
    blockchain: MaybeRefOrGetter<string> = Blockchain.ETH,
  ): ComputedRef<string | undefined> => useAddressInfo(address, 'source', blockchain);

  function getAddressName(address: string, blockchain: string = Blockchain.ETH): string | undefined {
    return resolveAddressInfo(address, 'name', blockchain);
  }

  /** True while an alias/ENS lookup for the address is in flight and nothing is cached yet. */
  function isAddressNamePending(address: string, blockchain: string = Blockchain.ETH): boolean {
    if (!get(enableAliasNames) || !address)
      return false;

    if (!isBlockchain(blockchain) || blockchain === Blockchain.ETH2)
      return false;

    const key = createKey(address, blockchain);
    return getIsPending(key) && !resolve(key);
  }

  function getAddressNameSource(address: string, blockchain: string = Blockchain.ETH): string | undefined {
    return resolveAddressInfo(address, 'source', blockchain);
  }

  const useAddressesWithoutNames = (blockchain?: MaybeRefOrGetter<string | null>): ComputedRef<string[]> => computed<string[]>(() => {
    const chain = blockchain ? toValue(blockchain) : undefined;
    const entries = !chain ? [...unknown.keys()] : [...unknown.keys()].filter(entry => entry.endsWith(`#${chain}`));
    return entries
      .map(entry => entry.split('#')[0])
      .filter(uniqueStrings);
  });

  function getChainsForAddress(address: string): string[] {
    if (isValidEthAddress(address))
      return get(evmChainIds);
    else if (isValidSolanaAddress(address))
      return get(solanaChainIds);
    else if (isValidBtcAddress(address) || isValidBchAddress(address))
      return get(bitcoinChainIds);
    else
      return get(allChainIds);
  }

  function resetAddressNamesData(items: AddressBookSimplePayload[]): void {
    for (const item of items) {
      const chains: string[] = item.blockchain
        ? [item.blockchain]
        : getChainsForAddress(item.address);

      for (const chain of chains) {
        refresh(createKey(item.address, chain));
      }
    }
  }

  function refreshAvatarTimestamp(): void {
    set(lastRefreshedAvatar, Date.now());
  }

  function updateEnsNamesAndReset(newResult: Record<string, string | null>): void {
    const currentNames = get(ensNames);
    const changed = Object.keys(newResult).filter(address => currentNames[address] !== newResult[address]);
    store.setEnsNames(newResult);

    if (changed.length > 0)
      resetAddressNamesData(changed.map(address => ({ address, blockchain: null })));
  }

  return {
    getAddressName,
    getAddressNameSource,
    getEnsName,
    isAddressNamePending,
    useEnsNamesList,
    refreshAvatarTimestamp,
    resetAddressNamesData,
    resetAddressesNames,
    updateEnsNamesAndReset,
    useAddressInfo,
    useAddressName,
    useAddressNameSource,
    useAddressesWithoutNames,
    useEnsAvatarUrl,
  };
});
