import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import { type MaybeRef } from '@vueuse/core';
import { useAddressesNamesApi } from '@/services/blockchain/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTasks } from '@/store/tasks';
import {
  AddressBookEntries,
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookSimplePayload,
  type EthNames
} from '@/types/eth-names';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueObjects, uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';
import { isValidEthAddress } from '@/utils/text';

export const useAddressesNamesStore = defineStore('addressesNames', () => {
  const { enableAliasNames } = storeToRefs(useFrontendSettingsStore());

  const fetchedEntries = ref<AddressBookSimplePayload[]>([]);
  const addressesNames = ref<AddressBookEntries>([]);

  const addressBookGlobal = ref<AddressBookEntries>([]);
  const addressBookPrivate = ref<AddressBookEntries>([]);

  const addressBookEntries = computed(() => {
    return {
      global: get(addressBookGlobal),
      private: get(addressBookPrivate)
    };
  });

  const { awaitTask } = useTasks();
  const { notify } = useNotificationsStore();
  const { t, tc } = useI18n();

  const {
    getEnsNames,
    getEnsNamesTask,
    getAddressesNames,
    getAddressBook,
    addAddressBook: addAddressBookCaller,
    deleteAddressBook: deleteAddressBookCaller,
    updateAddressBook: updateAddressBookCaller
  } = useAddressesNamesApi();

  const { isEvm } = useSupportedChains();

  const getFetchedAddressesList = (
    blockchain: MaybeRef<Blockchain | null>
  ): ComputedRef<string[]> =>
    computed(() => {
      return get(fetchedEntries)
        .filter(item => item.blockchain === blockchain)
        .map(({ address }) => address);
    });

  const fetchEnsNames = async (
    addresses: string[],
    forceUpdate = false
  ): Promise<void> => {
    if (addresses.length === 0) return;

    const filteredAddresses = addresses
      .filter(uniqueStrings)
      .filter(isValidEthAddress);

    if (filteredAddresses.length === 0) return;

    if (forceUpdate) {
      const taskType = TaskType.FETCH_ENS_NAMES;
      const { taskId } = await getEnsNamesTask(filteredAddresses);
      await awaitTask<EthNames, TaskMeta>(taskId, taskType, {
        title: tc('ens_names.task.title')
      });
    } else {
      await getEnsNames(filteredAddresses);
    }

    await fetchAddressesNames(filteredAddresses, Blockchain.ETH);
  };

  const addFetchedEntries = (newEntries: AddressBookSimplePayload[]) => {
    const arr = [...get(fetchedEntries), ...newEntries];
    const unique = uniqueObjects(
      arr,
      (item: AddressBookSimplePayload) => item.address + item.blockchain
    );
    set(fetchedEntries, unique);
  };

  const addSavedAddressesNames = (newEntries: AddressBookEntries) => {
    const arr = [...get(addressesNames), ...newEntries];
    const unique = uniqueObjects(
      arr,
      (item: AddressBookEntry) => item.address + item.blockchain
    );
    set(addressesNames, unique);
  };

  const fetchAddressesNames = async (
    addresses: string[] | null = null,
    blockchain: Blockchain | undefined = undefined
  ): Promise<void> => {
    let payload: AddressBookSimplePayload[];

    if (addresses !== null && blockchain !== undefined) {
      if (!get(isEvm(blockchain))) return;

      payload = addresses.map(address => ({ address, blockchain }));
      addFetchedEntries(payload);
    } else {
      payload = uniqueObjects(
        [
          ...get(addressBookGlobal).map(item => ({
            address: item.address,
            blockchain: item.blockchain
          })),
          ...get(addressBookPrivate).map(item => ({
            address: item.address,
            blockchain: item.blockchain
          })),
          ...get(fetchedEntries)
        ],
        item => item.address + item.blockchain
      );
    }

    payload = payload.filter(item => !!item).filter(uniqueStrings);

    try {
      const result = await getAddressesNames(payload);
      addSavedAddressesNames(AddressBookEntries.parse(result));
    } catch (e: any) {
      logger.error(e);
      const message = e?.message ?? e ?? '';
      notify({
        title: tc('alias_names.error.title'),
        message: tc('alias_names.error.message', 0, { message }),
        display: true
      });
    }
  };

  const addressNameSelector = (
    address: string,
    blockchain: Blockchain = Blockchain.ETH
  ) =>
    computed<string | null>(() => {
      if (!get(enableAliasNames)) return null;

      const found = get(addressesNames).filter(
        item =>
          item.address === address &&
          (item.blockchain === blockchain || item.blockchain === null)
      );

      if (found.length === 0) return null;
      if (found.length === 1) return found[0].name;

      return found.find(item => item.blockchain !== null)?.name ?? null;
    });

  const updateAddressBookState = async (
    location: AddressBookLocation,
    result: AddressBookEntries
  ) => {
    if (location === 'global') {
      set(addressBookGlobal, result);
    } else {
      set(addressBookPrivate, result);
    }

    await fetchAddressesNames();
  };

  const fetchAddressBook = async (
    location: AddressBookLocation,
    addresses?: string[]
  ) => {
    const notifyError = (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        title: t('address_book.actions.fetch.error.title').toString(),
        message: t('address_book.actions.fetch.error.message', {
          message
        }).toString(),
        display: true
      });
    };
    try {
      const result = await getAddressBook(location, addresses);
      await updateAddressBookState(location, result);
    } catch (e: any) {
      notifyError(e);
    }
  };

  const addAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries
  ) => {
    const result = await addAddressBookCaller(location, entries);

    if (result) {
      await fetchAddressBook(location);
    }
  };

  const updateAddressBook = async (
    location: AddressBookLocation,
    entries: AddressBookEntries
  ) => {
    const result = await updateAddressBookCaller(location, entries);

    if (result) {
      await fetchAddressBook(location);
    }
  };

  const deleteAddressBook = async (
    location: AddressBookLocation,
    addresses: AddressBookSimplePayload[]
  ) => {
    const result = await deleteAddressBookCaller(location, addresses);

    if (result) {
      await fetchAddressBook(location);
    }
  };

  return {
    fetchEnsNames,
    fetchedEntries,
    getFetchedAddressesList,
    addressesNames,
    addressNameSelector,
    addressBookEntries,
    fetchAddressesNames,
    fetchAddressBook,
    addAddressBook,
    updateAddressBook,
    deleteAddressBook
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAddressesNamesStore, import.meta.hot)
  );
}
