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
import type { TaskMeta } from '@/types/task';
import type { MaybeRef } from '@vueuse/core';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useSupportedChains } from '@/composables/info/chains';
import { useItemCache } from '@/composables/item-cache';
import { useNotificationsStore } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTaskStore } from '@/store/tasks';
import { isBlockchain } from '@/types/blockchain/chains';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { defaultCollectionState } from '@/utils/collection';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';
import { Blockchain, isValidBtcAddress, isValidEthAddress } from '@rotki/common';

export const useAddressesNamesStore = defineStore('blockchains/accounts/addresses-names', () => {
  const { enableAliasNames } = storeToRefs(useFrontendSettingsStore());

  const fetchedEntries = ref<AddressBookSimplePayload[]>([]);
  const addressesNames = ref<AddressBookEntries>([]);
  const ensNames = ref<EthNames>({});

  const { awaitTask } = useTaskStore();
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
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

  const getEnsAvatarUrl = (address: MaybeRef<string>): ComputedRef<string | null> => computed<string | null>(() => {
    const ens = get(ensNameSelector(address));
    if (!ens)
      return null;

    return ensAvatarUrl(ens, get(lastRefreshedAvatar));
  });

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
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        display: true,
        message: t('alias_names.error.message', { message }),
        title: t('alias_names.error.title'),
      });
      result = [];
    }

    return function* (): Generator<{ key: string; item: string }, void> {
      for (const entry of payload) {
        const key = createKey(entry.address, entry.blockchain);

        const item = result.find(
          res =>
            res.address === entry.address
            && res.blockchain === entry.blockchain,
        )?.name || '';

        yield { item, key };
      }
    };
  };

  const {
    isPending,
    refresh,
    reset: resetAddressesNames,
    retrieve,
    unknown,
  } = useItemCache<string>(async keys => fetchAddressesNames(keys));

  const getAddressesWithoutNames = (blockchain?: MaybeRef<string | null>): ComputedRef<string[]> => computed<string[]>(() => {
    const chain = get(blockchain);
    const entries = !chain ? [...unknown.keys()] : [...unknown.keys()].filter(entry => entry.endsWith(`#${chain}`));
    return entries
      .map(entry => entry.split('#')[0])
      .filter(uniqueStrings);
  });

  const addressNameSelector = (
    address: MaybeRef<string>,
    blockchain: MaybeRef<string> = Blockchain.ETH,
  ): ComputedRef<string | null> => computed<string | null>(() => {
    const addressVal = get(address);
    if (!get(enableAliasNames) || !addressVal)
      return null;

    const chain = get(blockchain);

    if (!isBlockchain(chain) || chain === Blockchain.ETH2)
      return null;

    const key = createKey(addressVal, chain);

    const cachedName = get(retrieve(key));

    // We keep track of the pending status to refresh, but if there is already a
    // value in cache we return that instead of null until a new value is presented
    if (get(isPending(key) && !cachedName))
      return null;

    return cachedName || null;
  });

  const getChainsForAddress = (address: string): string[] => {
    // Determine appropriate chains based on address type
    if (isValidEthAddress(address)) {
      // ETH address - check EVM and EVM-like chains
      return get(supportedChains)
        .filter(chain => ['evm', 'evmlike'].includes(chain.type))
        .map(chain => chain.id);
    }
    else if (isValidBtcAddress(address)) {
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
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        display: true,
        message: t('address_book.actions.fetch.error.message', {
          message,
        }),
        title: t('address_book.actions.fetch.error.title'),
      });

      return defaultCollectionState();
    }
  };

  const addAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries,
  ): Promise<boolean> => {
    const result = await addAddressBookCaller(location, entries);

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
      const taskType = TaskType.FETCH_ENS_NAMES;
      const { taskId } = await getEnsNamesTask(filteredAddresses);
      try {
        const { result } = await awaitTask<EthNames, TaskMeta>(
          taskId,
          taskType,
          {
            title: t('ens_names.task.title'),

          },
        );
        newResult = result;
      }
      catch (error: any) {
        if (!isTaskCancelled(error)) {
          notify({
            display: true,
            message: t('ens_names.error.message', { message: error.message }),
            title: t('ens_names.task.title'),
          });
        }
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
    addressesNames,
    addressNameSelector,
    deleteAddressBook,
    ensNames,
    ensNameSelector,
    fetchedEntries,
    fetchEnsNames,
    getAddressBook,
    getAddressesWithoutNames,
    getEnsAvatarUrl,
    resetAddressesNames,
    resetAddressNamesData,
    setLastRefreshedAvatar,
    updateAddressBook,
    updateEnsNamesState,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAddressesNamesStore, import.meta.hot));
