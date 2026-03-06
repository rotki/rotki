import type { MaybeRef, MaybeRefOrGetter } from 'vue';
import type { TaskMeta } from '@/modules/tasks/types';
import type { Collection } from '@/types/collection';
import type {
  AddressBookEntries,
  AddressBookEntry,
  AddressBookLocation,
  AddressBookRequestPayload,
  AddressBookSimplePayload,
  AddressNameRequestPayload,
  EthNames,
} from '@/types/eth-names';
import { Blockchain, isValidBchAddress, isValidBtcAddress, isValidEthAddress, isValidSolanaAddress } from '@rotki/common';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useSupportedChains } from '@/composables/info/chains';
import { createItemCache } from '@/composables/item-cache';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { isBlockchain } from '@/types/blockchain/chains';
import { defaultCollectionState } from '@/utils/collection';
import { uniqueStrings } from '@/utils/data';
import { getErrorMessage } from '@/utils/error-handling';
import { logger } from '@/utils/logging';

export const useAddressesNamesStore = defineStore('blockchains/accounts/addresses-names', () => {
  const { enableAliasNames } = storeToRefs(useFrontendSettingsStore());

  const ensNames = shallowRef<EthNames>({});

  const { runTask } = useTaskHandler();
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { supportedChains } = useSupportedChains();

  const {
    addAddressBook: addAddressBookCaller,
    deleteAddressBook: deleteAddressBookCaller,
    ensAvatarUrl,
    fetchAddressBook,
    getAddressesNames,
    getEnsNames,
    getEnsNamesTask,
    updateAddressBook: updateAddressBookCaller,
  } = useAddressesNamesApi();

  const lastRefreshedAvatar = ref<number>(0);

  const setLastRefreshedAvatar = (): void => {
    set(lastRefreshedAvatar, Date.now());
  };

  setLastRefreshedAvatar();

  const ensNameSelector = (address: MaybeRef<string>): ComputedRef<string | null> => computed<string | null>(() => {
    if (!get(enableAliasNames))
      return null;

    return get(ensNames)[get(address)] || null;
  });

  function getEnsName(address: string): string | null {
    if (!get(enableAliasNames))
      return null;

    return get(ensNames)[address] || null;
  }

  const useEnsAvatarUrl = (address: MaybeRefOrGetter<string>): ComputedRef<string | null> => computed<string | null>(() => {
    const ens = getEnsName(toValue(address));
    if (!ens)
      return null;

    return ensAvatarUrl(ens, get(lastRefreshedAvatar));
  });

  function getEnsAvatarUrl(address: string): string | null {
    const ens = getEnsName(address);
    if (!ens)
      return null;

    return ensAvatarUrl(ens, get(lastRefreshedAvatar));
  }

  const createKey = (address: string, chain: string): string => `${address}#${chain}`;

  const fetchAddressesNames = async (keys: string[]) => {
    const payload: AddressNameRequestPayload[] = [];
    keys.forEach((key) => {
      const [address, blockchain] = key.split('#');
      if (isBlockchain(blockchain))
        payload.push({ address, blockchain });
    });

    let result: AddressBookEntries;
    try {
      result = await getAddressesNames(payload);
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(t('alias_names.error.title'), t('alias_names.error.message', { message: getErrorMessage(error) }));
      result = [];
    }

    const resultMap = new Map<string, AddressBookEntry>();
    for (const entry of result) resultMap.set(createKey(entry.address, entry.blockchain ?? ''), entry);

    return function* (): Generator<{ key: string; item: AddressBookEntry | undefined }, void> {
      for (const entry of payload) {
        const key = createKey(entry.address, entry.blockchain);
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
  } = createItemCache<AddressBookEntry | undefined>(async keys => fetchAddressesNames(keys));

  const getAddressesWithoutNames = (blockchain?: MaybeRef<string | null>): ComputedRef<string[]> => computed<string[]>(() => {
    const chain = get(blockchain);
    const entries = !chain ? [...unknown.keys()] : [...unknown.keys()].filter(entry => entry.endsWith(`#${chain}`));
    return entries
      .map(entry => entry.split('#')[0])
      .filter(uniqueStrings);
  });

  const addressInfoSelector = <T extends keyof AddressBookEntry>(
    address: MaybeRef<string>,
    field: T,
    blockchain: MaybeRef<string> = Blockchain.ETH,
  ): ComputedRef<AddressBookEntry[T] | undefined> => computed<AddressBookEntry[T] | undefined>(() => {
    const addressVal = get(address);
    if (!get(enableAliasNames) || !addressVal)
      return undefined;

    const chain = get(blockchain);

    if (!isBlockchain(chain) || chain === Blockchain.ETH2)
      return undefined;

    const key = createKey(addressVal, chain);

    const cachedInfo = resolve(key);

    // We keep track of the pending status to refresh, but if there is already a
    // value in cache we return that instead of null until a new value is presented
    if (getIsPending(key) && !cachedInfo)
      return undefined;

    return cachedInfo?.[field] || undefined;
  });

  const addressNameSelector = (
    address: MaybeRef<string>,
    blockchain: MaybeRef<string> = Blockchain.ETH,
  ): ComputedRef<string | undefined> => addressInfoSelector(address, 'name', blockchain);

  const addressNameSourceSelector = (
    address: MaybeRef<string>,
    blockchain: MaybeRef<string> = Blockchain.ETH,
  ): ComputedRef<string | undefined> => addressInfoSelector(address, 'source', blockchain);

  function getAddressInfo<T extends keyof AddressBookEntry>(
    address: string,
    field: T,
    blockchain: string = Blockchain.ETH,
  ): AddressBookEntry[T] | undefined {
    const addressVal = address;
    if (!get(enableAliasNames) || !addressVal)
      return undefined;

    if (!isBlockchain(blockchain) || blockchain === Blockchain.ETH2)
      return undefined;

    const key = createKey(addressVal, blockchain);
    const cachedInfo = resolve(key);

    if (getIsPending(key) && !cachedInfo)
      return undefined;

    return cachedInfo?.[field] || undefined;
  }

  function getAddressName(address: string, blockchain: string = Blockchain.ETH): string | undefined {
    return getAddressInfo(address, 'name', blockchain);
  }

  function getAddressNameSource(address: string, blockchain: string = Blockchain.ETH): string | undefined {
    return getAddressInfo(address, 'source', blockchain);
  }

  const getChainsForAddress = (address: string): string[] => {
    // Determine appropriate chains based on address type
    if (isValidEthAddress(address)) {
      // ETH address - check EVM and EVM-like chains
      return get(supportedChains)
        .filter(chain => ['evm', 'evmlike'].includes(chain.type))
        .map(chain => chain.id);
    }
    else if (isValidSolanaAddress(address)) {
      // Solana address - check Solana chains only
      return get(supportedChains)
        .filter(chain => chain.type === 'solana')
        .map(chain => chain.id);
    }
    else if (isValidBtcAddress(address) || isValidBchAddress(address)) {
      // Bitcoin address - check Bitcoin chains only
      return get(supportedChains)
        .filter(chain => chain.type === 'bitcoin')
        .map(chain => chain.id);
    }
    else {
      // Unknown address type - check all chains as fallback
      return get(supportedChains).map(chain => chain.id);
    }
  };

  const resetAddressNamesData = (items: AddressBookSimplePayload[]): void => {
    items.forEach((item) => {
      const chains: string[] = item.blockchain
        ? [item.blockchain]
        : getChainsForAddress(item.address);

      chains.forEach((chain) => {
        const key = createKey(item.address, chain);
        refresh(key);
      });
    });
  };

  const getAddressBook = async (
    location: AddressBookLocation,
    payload: MaybeRef<AddressBookRequestPayload>,
  ): Promise<Collection<AddressBookEntry>> => {
    try {
      return await fetchAddressBook(location, get(payload));
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(
        t('address_book.actions.fetch.error.title'),
        t('address_book.actions.fetch.error.message', {
          message: getErrorMessage(error),
        }),
      );

      return defaultCollectionState();
    }
  };

  const addAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries,
    updateExisting = false,
  ): Promise<boolean> => {
    const result = await addAddressBookCaller(location, entries, updateExisting);

    if (result)
      resetAddressNamesData(entries);

    return result;
  };

  const updateAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries,
  ): Promise<boolean> => {
    const result = await updateAddressBookCaller(location, entries);

    if (result)
      resetAddressNamesData(entries);

    return result;
  };

  const deleteAddressBook = async (
    location: AddressBookLocation,
    addresses: AddressBookSimplePayload[],
  ): Promise<boolean> => {
    const result = await deleteAddressBookCaller(location, addresses);

    if (result)
      resetAddressNamesData(addresses);

    return result;
  };

  const updateEnsNamesState = (newResult: Record<string, string | null>, skipReset = false): void => {
    const oldEnsNames = {
      ...get(ensNames),
    };

    set(ensNames, {
      ...oldEnsNames,
      ...newResult,
    });

    if (!skipReset) {
      const addresses = Object.keys(newResult);
      resetAddressNamesData(addresses.map(address => ({ address, blockchain: null })));
    }
  };

  const fetchEnsNames = async (
    payload: AddressBookSimplePayload[],
    forceUpdate = false,
  ): Promise<void> => {
    if (payload.length === 0)
      return;

    const filteredAddresses = payload
      .map(({ address }) => address)
      .filter(uniqueStrings)
      .filter(isValidEthAddress);

    if (filteredAddresses.length === 0)
      return;

    let newResult: Record<string, string | null> = {};

    if (forceUpdate) {
      const outcome = await runTask<EthNames, TaskMeta>(
        async () => getEnsNamesTask(filteredAddresses),
        { type: TaskType.FETCH_ENS_NAMES, meta: { title: t('ens_names.task.title') } },
      );

      if (outcome.success) {
        newResult = outcome.result;
      }
      else if (isActionableFailure(outcome)) {
        notifyError(t('ens_names.task.title'), t('ens_names.error.message', { message: outcome.message }));
      }
    }
    else {
      newResult = await getEnsNames(filteredAddresses);
    }

    const payloadToReset = payload.filter(({ address }) => get(ensNames)[address] !== newResult[address]);
    resetAddressNamesData(payloadToReset);

    updateEnsNamesState(newResult, true);
  };

  return {
    addAddressBook,
    addressInfoSelector,
    addressNameSelector,
    addressNameSourceSelector,
    deleteAddressBook,
    ensNames,
    ensNameSelector,
    fetchEnsNames,
    getAddressBook,
    getAddressName,
    getAddressNameSource,
    getAddressesWithoutNames,
    getEnsAvatarUrl,
    getEnsName,
    resetAddressesNames,
    resetAddressNamesData,
    setLastRefreshedAvatar,
    updateAddressBook,
    updateEnsNamesState,
    useEnsAvatarUrl,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAddressesNamesStore, import.meta.hot));
