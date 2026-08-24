import type { ComputedRef, Ref } from 'vue';
import { isValidEthAddress } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useAddressBookOperations } from '@/modules/accounts/address-book/use-address-book-operations';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { uniqueObjects } from '@/modules/core/common/data/data';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

export interface RecipientOption {
  address: string;
  name?: string;
}

interface UseTradeRecipientAddressReturn {
  /** All bound with `v-model`, so they stay writable. */
  modelSearchValue: Ref<string>;
  modelAddressBookSearch: Ref<string>;
  modelOpenSuggestionsMenu: Ref<boolean>;
  modelOpenOptionsDialog: Ref<boolean>;
  /** Empty is allowed; anything else has to be an address. */
  valid: ComputedRef<boolean>;
  resolvingEns: Readonly<Ref<boolean>>;
  /**
   * What the typed search found, ready to be picked. Shallow: a deep `readonly()` would turn the
   * options into a `DeepReadonly` the display component's prop cannot take.
   */
  directOptions: Readonly<Ref<RecipientOption[]>>;
  /** Every tracked address that could receive, so never the connected one. */
  trackedAddresses: ComputedRef<string[]>;
  filteredAddressBookOptions: ComputedRef<string[]>;
  select: (address: string) => void;
  reset: () => void;
  /** Takes a typed address as the recipient, ignoring anything that is not one. */
  applySearchInput: () => void;
  /** The input and the menu gaining or losing focus together. */
  handleFocusChange: (focused: boolean) => void;
  searchAddresses: (value: string) => Promise<void>;
}

/**
 * Picking who a trade is sent to.
 *
 * There are three ways in: typing, which searches the private address book, the tracked accounts
 * and ENS at once; the address book dialog; and pasting an address, which is taken as-is. The
 * connected account is filtered out of all of them, because sending to yourself is not the intent
 * here, and it is dropped from the model if it becomes the connected account later.
 */
export function useTradeRecipientAddress(model: Ref<string>): UseTradeRecipientAddressReturn {
  const modelSearchValue = shallowRef<string>('');
  const modelAddressBookSearch = shallowRef<string>('');
  const modelOpenSuggestionsMenu = shallowRef<boolean>(false);
  const modelOpenOptionsDialog = shallowRef<boolean>(false);
  const resolvingEns = shallowRef<boolean>(false);
  const addressBookOptions = ref<string[]>([]);
  const directOptions = ref<RecipientOption[]>([]);

  const debouncedSearchValue = refDebounced(modelSearchValue, 200);
  const debouncedAddressBookSearch = refDebounced(modelAddressBookSearch, 200);

  const { connectedAddress } = storeToRefs(useWalletStore());
  const { addresses } = useAccountAddresses();
  const { getAddressBook } = useAddressBookOperations();
  const { fetchEnsNames, resolveEnsToAddress } = useEnsOperations();

  function isNotConnectedAddress(address: string): boolean {
    const connected = get(connectedAddress);
    return !connected || address !== connected;
  }

  const trackedAddresses = computed<string[]>(() => {
    const accountsAddresses = [...new Set(Object.values(get(addresses)).flat())];
    return accountsAddresses.filter(address => isValidEthAddress(address) && isNotConnectedAddress(address));
  });

  const filteredAddressBookOptions = computed<string[]>(
    () => get(addressBookOptions).filter(isNotConnectedAddress),
  );

  const valid = computed<boolean>(() => {
    const value = get(model);
    return !value || isValidEthAddress(value);
  });

  function select(address: string): void {
    if (isNotConnectedAddress(address)) {
      set(model, address);
    }
    set(modelOpenOptionsDialog, false);
    set(modelOpenSuggestionsMenu, false);
    set(modelSearchValue, '');
  }

  function reset(): void {
    set(model, '');
  }

  function applySearchInput(): void {
    const value = get(modelSearchValue);
    if (isValidEthAddress(value)) {
      select(value);
    }
  }

  function handleFocusChange(focused: boolean): void {
    set(modelOpenSuggestionsMenu, focused);
    if (focused)
      return;

    const search = get(modelSearchValue);
    if (search && isValidEthAddress(search)) {
      set(model, search);
    }
    else {
      set(modelSearchValue, '');
    }
  }

  async function getAddressBookData(name: string): Promise<RecipientOption[]> {
    const data = await getAddressBook('private', {
      limit: 10,
      nameSubstring: name,
      offset: 0,
    });

    return data.data
      .filter(item => isValidEthAddress(item.address))
      .map(item => ({ address: item.address, name: item.name }));
  }

  async function searchAddresses(value: string): Promise<void> {
    const values: RecipientOption[] = [...await getAddressBookData(value)];

    values.push(...get(trackedAddresses)
      .filter(item => item.includes(value))
      .map(item => ({ address: item })));

    if (value.endsWith('.eth')) {
      set(resolvingEns, true);
      const address = await resolveEnsToAddress(value);
      set(resolvingEns, false);
      if (address) {
        values.push({ address, name: value });
      }
    }
    else if (isValidEthAddress(value)) {
      // The name is looked up for display only, so it does not hold the option up.
      startPromise(fetchEnsNames([{ address: value, blockchain: null }]));
      values.push({ address: value });
    }

    set(directOptions, uniqueObjects(values.filter(item => isNotConnectedAddress(item.address)), item => item.address));
  }

  async function fetchAddressBookAddresses(name: string): Promise<void> {
    const data = await getAddressBookData(name);
    set(addressBookOptions, data.map(item => item.address));
  }

  watch([debouncedAddressBookSearch, modelOpenOptionsDialog], ([search, dialogOpen]) => {
    if (dialogOpen) {
      startPromise(fetchAddressBookAddresses(search));
    }
    else {
      set(modelAddressBookSearch, '');
    }
  });

  watch(debouncedSearchValue, (value) => {
    startPromise(searchAddresses(value));
  });

  watch(modelOpenSuggestionsMenu, (curr, prev) => {
    if (!curr && prev) {
      applySearchInput();
    }
  });

  watch(connectedAddress, (address) => {
    if (address && address === get(model)) {
      reset();
    }
  });

  return {
    applySearchInput,
    directOptions: shallowReadonly(directOptions),
    filteredAddressBookOptions,
    handleFocusChange,
    modelAddressBookSearch,
    modelOpenOptionsDialog,
    modelOpenSuggestionsMenu,
    modelSearchValue,
    reset,
    resolvingEns: readonly(resolvingEns),
    searchAddresses,
    select,
    trackedAddresses,
    valid,
  };
}
