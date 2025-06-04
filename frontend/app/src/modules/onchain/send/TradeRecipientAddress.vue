<script setup lang="ts">
import type { AddressBookEntry } from '@/types/eth-names';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import TradeAddressDisplay from '@/modules/onchain/send/TradeAddressDisplay.vue';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { uniqueObjects } from '@/utils/data';
import { isValidEthAddress } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useTemplateRef } from 'vue';

const model = defineModel<string>({ required: true });

defineProps<{
  chain: string;
  showWarning: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const openOptionsDialog = ref<boolean>(false);

const resolvingEns = ref<boolean>(false);
const addressBookOptions = ref<string[]>([]);
const addressBookSearch = ref<string>('');
const addressBookSearchDebounced = refDebounced(addressBookSearch, 200);

const openSuggestionsMenu = ref<boolean>(false);
const searchValue = ref<string>('');
const directOptions = ref<{ address: string; name: string }[]>([]);
const debouncedSearchValue = refDebounced(searchValue, 200);

const searchInputRef = useTemplateRef<InstanceType<typeof HTMLInputElement>>('searchInputRef');
const menuContainerRef = useTemplateRef<InstanceType<typeof HTMLDivElement>>('menuContainerRef');
const { focused: searchInputFocused } = useFocus(searchInputRef);
const { focused: menuFocusedWithin } = useFocusWithin(menuContainerRef);

const { connected, connectedAddress } = storeToRefs(useWalletStore());
const { addresses } = useAccountAddresses();
const { fetchAddressBook, resolveEnsNames } = useAddressesNamesApi();
const { fetchEnsNames, updateEnsNamesState } = useAddressesNamesStore();

function isNotConnectedAddress(address: string) {
  const connected = get(connectedAddress);
  return !connected || address !== connected;
}

const trackedAddresses = computed<string[]>(() => {
  const accountsAddresses = [...new Set(Object.values(get(addresses)).flat())];
  return accountsAddresses.filter(address => isValidEthAddress(address) && isNotConnectedAddress(address));
});

const filteredAddressBookOptions = computed<string[]>(() => get(addressBookOptions).filter(isNotConnectedAddress));

const valid = computed<boolean>(() => {
  const value = get(model);
  return !value || isValidEthAddress(value);
});

const anyFocused = logicOr(searchInputFocused, menuFocusedWithin);
const focusDebounced = refDebounced(anyFocused, 200);
const usedAnyFocused = logicAnd(anyFocused, focusDebounced);

function select(address: string) {
  if (isNotConnectedAddress(address)) {
    set(model, address);
  }
  set(openOptionsDialog, false);
  set(openSuggestionsMenu, false);
  set(searchValue, '');
}

async function getAddressBookData(name: string): Promise<AddressBookEntry[]> {
  const data = await fetchAddressBook('private', {
    limit: 10,
    nameSubstring: name,
    offset: 0,
  });

  return data.data.filter(item => isValidEthAddress(item.address));
}

async function fetchAddressBookAddresses(name: string) {
  const data = await getAddressBookData(name);
  const addresses = data.map(item => item.address);
  set(addressBookOptions, addresses);
}

function resetModelValue() {
  set(model, '');
}

watch([addressBookSearchDebounced, openOptionsDialog], ([search, openOptionsDialog]) => {
  if (openOptionsDialog) {
    fetchAddressBookAddresses(search);
  }
  else {
    set(addressBookSearch, '');
  }
});

watch(usedAnyFocused, (focus) => {
  set(openSuggestionsMenu, focus);
  if (!focus) {
    const search = get(searchValue);
    if (search && isValidEthAddress(search)) {
      set(model, search);
    }
    else {
      set(searchValue, '');
    }
  }
});

watch(debouncedSearchValue, async (value) => {
  const values = [];
  const privateBooks = await getAddressBookData(value);
  if (privateBooks.length > 0) {
    values.push(...privateBooks);
  }

  const tracked = get(trackedAddresses).filter(item => item.includes(value));
  if (tracked.length > 0) {
    values.push(...tracked.map(item => ({ address: item })));
  }

  if (value.endsWith('.eth')) {
    set(resolvingEns, true);
    const address = await resolveEnsNames(value);
    set(resolvingEns, false);
    if (address && isValidEthAddress(address)) {
      values.push({
        address,
        name: value,
      });

      updateEnsNamesState({
        [address]: value,
      });
    }
  }
  else if (isValidEthAddress(value)) {
    startPromise(fetchEnsNames([{ address: value, blockchain: null }]));
    values.push({
      address: value,
    });
  }

  set(directOptions, uniqueObjects(values.filter(item => isNotConnectedAddress(item.address)), item => item.address));
});

watch(connectedAddress, (connectedAddress) => {
  if (connectedAddress && connectedAddress === get(model)) {
    set(model, '');
  }
});

const { containerProps: trackedContainerProps, list: trackedList, wrapperProps: trackedWrapperProps } = useVirtualList(trackedAddresses, {
  itemHeight: 56,
});

const { containerProps: addressBookContainerProps, list: addressBookList, wrapperProps: addressBookWrapperProps } = useVirtualList(filteredAddressBookOptions, {
  itemHeight: 56,
});

function applySearchInput() {
  const value = get(searchValue);
  if (isValidEthAddress(value)) {
    select(value);
  }
}

watch(openSuggestionsMenu, (curr, prev) => {
  if (!curr && prev) {
    applySearchInput();
  }
});
</script>

<template>
  <RuiMenu
    v-model="openSuggestionsMenu"
    wrapper-class="w-full"
  >
    <template #activator>
      <div
        class="flex items-center bg-rui-grey-50 dark:bg-rui-grey-900 rounded-lg border border-default mt-1 duration-50 w-full"
        :class="{
          '!border-rui-error': !valid,
        }"
      >
        <div
          v-if="model"
          class="flex w-full justify-between gap-2 p-3"
        >
          <TradeAddressDisplay
            dense
            :chain="chain"
            :address="model"
            readonly
          />
          <RuiButton
            icon
            variant="text"
            @click="resetModelValue()"
          >
            <RuiIcon
              name="lu-x"
              size="18"
            />
          </RuiButton>
        </div>
        <template v-else>
          <label class="flex flex-col flex-1 p-3">
            <Transition
              mode="out-in"
              enter-active-class="transition-all duration-50"
              leave-active-class="transition-all duration-50"
              enter-from-class="opacity-0 -translate-x-1"
              leave-to-class="opacity-0 translate-x-1"
            >
              <span
                v-if="!model || valid"
                class="text-sm text-rui-grey-500 font-medium block"
              >
                {{ t('trade.to_address.label') }}
              </span>
              <span
                v-else
                class="text-sm text-rui-error font-medium block"
              >
                {{ t('trade.to_address.error') }}
              </span>
            </Transition>
            <input
              ref="searchInputRef"
              v-model="searchValue"
              type="text"
              class="outline-none w-full bg-transparent text-sm placeholder:text-rui-grey-400 dark:placeholder:text-rui-grey-700"
              placeholder="E.g. 0x9531c059098e3d194ff87febb587ab07b30b1306"
              @click="openSuggestionsMenu = true"
              @blur="applySearchInput()"
            />
          </label>
          <div class="p-3 pl-0">
            <RuiButton
              variant="outlined"
              color="primary"
              class="!p-3"
              @click="openOptionsDialog = true"
            >
              <RuiIcon
                name="lu-book-user"
                size="18"
              />
            </RuiButton>
          </div>
        </template>
      </div>
    </template>
    <template #default="{ width }">
      <div
        v-if="resolvingEns"
        class="p-4 w-full"
        :style="{ width: `${width}px` }"
      >
        {{ t('trade.recipient.resolving_ens') }}
      </div>
      <div
        v-else-if="directOptions.length > 0"
        ref="menuContainerRef"
        tabindex="-1"
        class="w-full py-2"
        :style="{ width: `${width}px` }"
      >
        <TradeAddressDisplay
          v-for="option in directOptions"
          :key="option.address"
          :address="option.address"
          :name="option.name"
          :chain="chain"
          @click="select(option.address)"
        />
      </div>
    </template>
  </RuiMenu>

  <RuiAlert
    v-if="connected && model && showWarning"
    type="warning"
    class="mt-2"
  >
    {{ t('trade.never_interacted') }}
  </RuiAlert>
  <RuiDialog
    v-model="openOptionsDialog"
    max-width="500"
  >
    <RuiCard
      divide
      no-padding
      content-class="overflow-hidden pb-2"
    >
      <template #header>
        {{ t('trade.recipient.select_recipient_address') }}
      </template>
      <RuiButton
        variant="text"
        class="absolute top-2 right-2"
        icon
        @click="openOptionsDialog = false"
      >
        <RuiIcon
          class="text-white"
          name="lu-x"
        />
      </RuiButton>
      <div class="flex flex-col max-h-[calc(100vh-200px)] overflow-hidden">
        <div class="flex flex-1 flex-col relative overflow-hidden">
          <div class="uppercase text-xs font-medium px-4 border-b border-default py-2 bg-rui-grey-50 dark:bg-rui-grey-900">
            {{ t('trade.recipient.tracked_addresses') }}
          </div>
          <div
            v-if="trackedAddresses.length === 0"
            class="p-4 text-rui-text-secondary"
          >
            {{ t('trade.recipient.no_addresses_found') }}
          </div>
          <div
            v-else
            class="flex-1"
            v-bind="trackedContainerProps"
          >
            <div v-bind="trackedWrapperProps">
              <TradeAddressDisplay
                v-for="address in trackedList"
                :key="address.data"
                :address="address.data"
                :chain="chain"
                @click="select(address.data)"
              />
            </div>
          </div>
        </div>
        <div class="flex flex-1 flex-col overflow-hidden border-t border-default">
          <div class="uppercase text-xs font-medium px-4 border-b border-default py-2">
            {{ t('trade.recipient.from_private_address_book') }}
          </div>
          <div class="p-4">
            <RuiTextField
              v-model="addressBookSearch"
              prepend-icon="lu-search"
              variant="outlined"
              dense
              hide-details
              color="primary"
              :label="t('common.actions.search')"
            />
          </div>
          <div
            v-if="filteredAddressBookOptions.length === 0"
            class="p-4 text-rui-text-secondary"
          >
            {{ t('trade.recipient.no_addresses_found') }}
          </div>
          <div
            v-else
            class="flex-1"
            v-bind="addressBookContainerProps"
          >
            <div v-bind="addressBookWrapperProps">
              <TradeAddressDisplay
                v-for="address in addressBookList"
                :key="address.data"
                :address="address.data"
                :chain="chain"
                @click="select(address.data)"
              />
            </div>
          </div>
        </div>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
