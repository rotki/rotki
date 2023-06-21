import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import {
  AddressBookEntries,
  type AddressBookLocation,
  type AddressBookSimplePayload,
  type EthNames
} from '@/types/eth-names';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type Chains } from '@/types/asset/asset-urls';
import { isBlockchain } from '@/types/blockchain/chains';

export const useAddressesNamesStore = defineStore(
  'blockchains/accounts/addresses-names',
  () => {
    const { enableAliasNames } = storeToRefs(useFrontendSettingsStore());

    const fetchedEntries = ref<AddressBookSimplePayload[]>([]);
    const addressesNames = ref<AddressBookEntries>([]);
    const ensNames = ref<EthNames>({});

    const addressBookGlobal = ref<AddressBookEntries>([]);
    const addressBookPrivate = ref<AddressBookEntries>([]);

    const addressBookEntries = computed(() => ({
      global: get(addressBookGlobal),
      private: get(addressBookPrivate)
    }));

    const { awaitTask } = useTaskStore();
    const { notify } = useNotificationsStore();
    const { t } = useI18n();

    const {
      getEnsNames,
      getEnsNamesTask,
      getAddressesNames,
      getAddressBook,
      ensAvatarUrl,
      addAddressBook: addAddressBookCaller,
      deleteAddressBook: deleteAddressBookCaller,
      updateAddressBook: updateAddressBookCaller
    } = useAddressesNamesApi();

    const lastRefreshedAvatar: Ref<number> = ref(0);

    const setLastRefreshedAvatar = () => {
      set(lastRefreshedAvatar, Date.now());
    };

    onBeforeMount(() => {
      setLastRefreshedAvatar();
    });

    const getFetchedAddressesList = (
      blockchain: MaybeRef<Blockchain | null>
    ): ComputedRef<string[]> =>
      computed(() =>
        get(fetchedEntries)
          .filter(item => item.blockchain === blockchain)
          .map(({ address }) => address)
      );

    const fetchEnsNames = async (
      payload: AddressBookSimplePayload[],
      forceUpdate = false
    ): Promise<void> => {
      if (payload.length === 0) {
        return;
      }

      const filteredAddresses = payload
        .map(({ address }) => address)
        .filter(uniqueStrings)
        .filter(isValidEthAddress);

      if (filteredAddresses.length === 0) {
        return;
      }

      if (forceUpdate) {
        const taskType = TaskType.FETCH_ENS_NAMES;
        const { taskId } = await getEnsNamesTask(filteredAddresses);
        const { result } = await awaitTask<EthNames, TaskMeta>(
          taskId,
          taskType,
          {
            title: t('ens_names.task.title')
          }
        );
        set(ensNames, {
          ...get(ensNames),
          ...result
        });
      } else {
        const result = await getEnsNames(filteredAddresses);

        set(ensNames, {
          ...get(ensNames),
          ...result
        });
      }

      startPromise(fetchAddressesNames(payload));
    };

    const addFetchedEntries = (newEntries: AddressBookSimplePayload[]) => {
      const arr = [...get(fetchedEntries), ...newEntries];
      const unique = uniqueObjects(
        arr,
        (item: AddressBookSimplePayload) => item.address + item.blockchain
      );
      set(fetchedEntries, unique);
    };

    const addSavedAddressesNames = (
      payload: AddressBookSimplePayload[],
      newEntries: AddressBookEntries
    ) => {
      const filtered = get(addressesNames).filter(
        item =>
          !payload.some(
            entry =>
              item.address === entry.address &&
              item.blockchain === entry.blockchain
          )
      );
      const newAddresses = [...filtered, ...newEntries];
      set(addressesNames, newAddresses);
    };

    const fetchAddressesNames = async (
      payload: AddressBookSimplePayload[] | null = null
    ): Promise<void> => {
      if (payload) {
        addFetchedEntries(payload);
      } else {
        payload = [
          ...get(addressBookGlobal).map(item => ({
            address: item.address,
            blockchain: item.blockchain
          })),
          ...get(addressBookPrivate).map(item => ({
            address: item.address,
            blockchain: item.blockchain
          })),
          ...get(fetchedEntries)
        ];
      }

      payload = uniqueObjects(payload, item => item.address + item.blockchain);

      try {
        const result = await getAddressesNames(payload);
        addSavedAddressesNames(payload, AddressBookEntries.parse(result));
      } catch (e: any) {
        logger.error(e);
        const message = e?.message ?? e ?? '';
        notify({
          title: t('alias_names.error.title'),
          message: t('alias_names.error.message', { message }),
          display: true
        });
      }
    };

    const ensNameSelector = (address: MaybeRef<string>) =>
      computed<string | null>(() => {
        if (!get(enableAliasNames)) {
          return null;
        }

        return get(ensNames)[get(address)] || null;
      });

    const getEnsAvatarUrl = (address: MaybeRef<string>) =>
      computed<string | null>(() => {
        const ens = get(ensNameSelector(address));
        if (!ens) {
          return null;
        }

        return ensAvatarUrl(ens, get(lastRefreshedAvatar));
      });

    const addressNameSelector = (
      address: MaybeRef<string>,
      blockchain: MaybeRef<Chains> = Blockchain.ETH
    ) =>
      computed<string | null>(() => {
        if (!get(enableAliasNames)) {
          return null;
        }

        let chain = get(blockchain);
        if (!isBlockchain(chain)) {
          chain = Blockchain.ETH;
        }
        const addr = get(address);
        const found = get(addressesNames).filter(
          item =>
            item.address === addr &&
            (item.blockchain === chain || item.blockchain === null)
        );

        if (found.length === 0) {
          return null;
        }
        if (found.length === 1) {
          return found[0].name;
        }

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
      ensNames,
      fetchEnsNames,
      fetchedEntries,
      getFetchedAddressesList,
      setLastRefreshedAvatar,
      addressesNames,
      ensNameSelector,
      getEnsAvatarUrl,
      addressNameSelector,
      addressBookEntries,
      fetchAddressesNames,
      fetchAddressBook,
      addAddressBook,
      updateAddressBook,
      deleteAddressBook
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAddressesNamesStore, import.meta.hot)
  );
}
