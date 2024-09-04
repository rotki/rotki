import { Blockchain } from '@rotki/common';
import { TaskType } from '@/types/task-type';
import { isBlockchain, isBtcChain } from '@/types/blockchain/chains';
import type { MaybeRef } from '@vueuse/core';
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
import type { Collection } from '@/types/collection';

export const useAddressesNamesStore = defineStore('blockchains/accounts/addresses-names', () => {
  const { enableAliasNames } = storeToRefs(useFrontendSettingsStore());

  const fetchedEntries = ref<AddressBookSimplePayload[]>([]);
  const addressesNames = ref<AddressBookEntries>([]);
  const ensNames = ref<EthNames>({});

  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const { supportedChains } = useSupportedChains();

  const {
    getEnsNames,
    getEnsNamesTask,
    getAddressesNames,
    ensAvatarUrl,
    fetchAddressBook,
    addAddressBook: addAddressBookCaller,
    deleteAddressBook: deleteAddressBookCaller,
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
        title: t('alias_names.error.title'),
        message: t('alias_names.error.message', { message }),
        display: true,
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

        yield { key, item };
      }
    };
  };

  const {
    isPending,
    retrieve,
    unknown,
    refresh,
    reset: resetAddressesNames,
  } = useItemCache<string>(keys => fetchAddressesNames(keys));

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

    if (!isBlockchain(chain) || isBtcChain(chain))
      return null;

    const key = createKey(addressVal, chain);

    const cachedName = get(retrieve(key));

    // We keep track of the pending status to refresh, but if there is already a
    // value in cache we return that instead of null until a new value is presented
    if (get(isPending(key) && !cachedName))
      return null;

    return cachedName || null;
  });

  const resetAddressNamesData = (items: AddressBookSimplePayload[]): void => {
    items.forEach((item) => {
      const chains: string[] = item.blockchain
        ? [item.blockchain]
        : get(supportedChains)
          .filter(chain => !isValidEthAddress(item.address) || ['evm', 'evmlike'].includes(chain.type))
          .map(chain => chain.id);

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
        title: t('address_book.actions.fetch.error.title').toString(),
        message: t('address_book.actions.fetch.error.message', {
          message,
        }),
        display: true,
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
            title: t('ens_names.task.title'),
            message: t('ens_names.error.message', { message: error.message }),
            display: true,
          });
        }
      }
    }
    else {
      newResult = await getEnsNames(filteredAddresses);
    }

    const payloadToReset = payload.filter(({ address }) => get(ensNames)[address] !== newResult[address]);

    set(ensNames, {
      ...get(ensNames),
      ...newResult,
    });
    resetAddressNamesData(payloadToReset);
  };

  return {
    ensNames,
    fetchEnsNames,
    fetchedEntries,
    getAddressesWithoutNames,
    setLastRefreshedAvatar,
    addressesNames,
    ensNameSelector,
    getEnsAvatarUrl,
    addressNameSelector,
    getAddressBook,
    addAddressBook,
    updateAddressBook,
    deleteAddressBook,
    resetAddressNamesData,
    resetAddressesNames,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAddressesNamesStore, import.meta.hot));
