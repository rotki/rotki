import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import {
  type AddressBookEntries,
  type AddressBookEntry,
  type AddressBookLocation,
  type AddressBookRequestPayload,
  type AddressBookSimplePayload,
  type AddressNameRequestPayload,
  type EthNames
} from '@/types/eth-names';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { isBlockchain } from '@/types/blockchain/chains';
import { type Collection } from '@/types/collection';
import { type Chains } from '@/types/asset/asset-urls';

export const useAddressesNamesStore = defineStore(
  'blockchains/accounts/addresses-names',
  () => {
    const { enableAliasNames } = storeToRefs(useFrontendSettingsStore());

    const fetchedEntries = ref<AddressBookSimplePayload[]>([]);
    const addressesNames = ref<AddressBookEntries>([]);
    const ensNames = ref<EthNames>({});

    const { awaitTask } = useTaskStore();
    const { t } = useI18n();

    const { notify } = useNotificationsStore();

    const {
      getEnsNames,
      getEnsNamesTask,
      getAddressesNames,
      ensAvatarUrl,
      fetchAddressBook,
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
        resetAddressesNames();
      } else {
        const result = await getEnsNames(filteredAddresses);

        set(ensNames, {
          ...get(ensNames),
          ...result
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

    const createKey = (address: string, blockchain: Blockchain) =>
      `${address}#${blockchain}`;

    const fetchAddressesNames = async (keys: string[]) => {
      const payload: AddressNameRequestPayload[] = [];
      keys.forEach(key => {
        const [address, blockchain] = key.split('#');
        if (isBlockchain(blockchain)) {
          payload.push({ address, blockchain });
        }
      });

      let result: AddressBookEntries;
      try {
        result = await getAddressesNames(payload);
      } catch (e: any) {
        logger.error(e);
        const message = e?.message ?? e ?? '';
        notify({
          title: t('alias_names.error.title'),
          message: t('alias_names.error.message', { message }),
          display: true
        });
        result = [];
      }

      return function* () {
        for (const entry of payload) {
          const key = createKey(entry.address, entry.blockchain);

          const item =
            result.find(
              res =>
                res.address === entry.address &&
                res.blockchain === entry.blockchain
            )?.name || '';

          yield { key, item };
        }
      };
    };

    const {
      isPending,
      retrieve,
      unknown,
      deleteCacheKey,
      reset: resetAddressesNames
    } = useItemCache<string>(keys => fetchAddressesNames(keys));

    const getAddressesWithoutNames = (): string[] => {
      const entries = unknown.keys();
      return [...entries]
        .map(entry => entry.split('#')[0])
        .filter(uniqueStrings);
    };

    const addressNameSelector = (
      address: MaybeRef<string>,
      blockchain: MaybeRef<Chains> = Blockchain.ETH
    ) =>
      computed<string | null>(() => {
        const addressVal = get(address);
        if (!get(enableAliasNames) || !isValidEthAddress(get(address))) {
          return null;
        }

        const chain = get(blockchain);

        if (!isBlockchain(chain)) {
          return null;
        }

        const key = createKey(addressVal, chain);

        if (get(isPending(key))) {
          return null;
        }

        return get(retrieve(key)) || null;
      });

    const resetAddressNamesData = (items: AddressBookSimplePayload[]) => {
      items.forEach(item => {
        const chains: Blockchain[] = item.blockchain
          ? [item.blockchain]
          : Object.values(Blockchain);

        chains.forEach(chain => {
          const key = createKey(item.address, chain);
          deleteCacheKey(key);
        });
      });
    };

    const getAddressBook = async (
      location: AddressBookLocation,
      payload: MaybeRef<AddressBookRequestPayload>
    ): Promise<Collection<AddressBookEntry>> => {
      try {
        return await fetchAddressBook(location, get(payload));
      } catch (e: any) {
        logger.error(e);
        const message = e?.message ?? e ?? '';
        notify({
          title: t('address_book.actions.fetch.error.title').toString(),
          message: t('address_book.actions.fetch.error.message', {
            message
          }).toString(),
          display: true
        });

        return defaultCollectionState();
      }
    };

    const addAddressBook = async (
      location: AddressBookLocation,
      entries: AddressBookEntries
    ) => {
      const result = await addAddressBookCaller(location, entries);

      if (result) {
        resetAddressNamesData(entries);
      }

      return result;
    };

    const updateAddressBook = async (
      location: AddressBookLocation,
      entries: AddressBookEntries
    ) => {
      const result = await updateAddressBookCaller(location, entries);

      if (result) {
        resetAddressNamesData(entries);
      }

      return result;
    };

    const deleteAddressBook = async (
      location: AddressBookLocation,
      addresses: AddressBookSimplePayload[]
    ) => {
      const result = await deleteAddressBookCaller(location, addresses);

      if (result) {
        resetAddressNamesData(addresses);
      }

      return result;
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
      resetAddressesNames
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAddressesNamesStore, import.meta.hot)
  );
}
