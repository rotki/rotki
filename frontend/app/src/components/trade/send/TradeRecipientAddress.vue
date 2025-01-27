<script setup lang="ts">
import TradeAddressDisplay from '@/components/trade/send/TradeAddressDisplay.vue';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useWalletStore } from '@/store/trade/wallet';
import { isValidEthAddress } from '@rotki/common';

const model = defineModel<string>({ required: true });

defineProps<{
  chain: string;
  showWarning: boolean;
}>();

const { t } = useI18n();

const openDialog = ref<boolean>(false);

const addressBookAddresses = ref<string[]>([]);
const addressBookSearch = ref<string>('');
const searchDebounced = refDebounced(addressBookSearch, 200);

const { connected, connectedAddress } = storeToRefs(useWalletStore());
const { addresses } = useAccountAddresses();
const { fetchAddressBook } = useAddressesNamesApi();

const trackedAddresses = computed(() => {
  const accountsAddresses = [...new Set(Object.values(get(addresses)).flat())];
  const connected = get(connectedAddress);

  return accountsAddresses.filter(address => isValidEthAddress(address) && (!connected || address !== connected));
});

function select(address: string) {
  set(model, address);
  set(openDialog, false);
}

async function fetchAddressBookData(name: string) {
  const data = await fetchAddressBook('private', {
    limit: 10,
    nameSubstring: name,
    offset: 0,
  });

  const addresses = data.data.map(item => item.address);
  set(addressBookAddresses, addresses);
}

watch([searchDebounced, openDialog], ([search, openDialog]) => {
  if (openDialog) {
    fetchAddressBookData(search);
  }
});
</script>

<template>
  <div class="flex items-center bg-rui-grey-50 dark:bg-rui-grey-900 rounded-lg border border-default mt-1">
    <label class="flex-1 p-3 block">
      <span class="text-sm text-rui-grey-500 font-medium">
        {{ t('trade.to_address') }}
      </span>
      <input
        v-model="model"
        type="text"
        class="outline-none w-full bg-transparent text-sm placeholder:text-rui-grey-300 dark:placeholder:text-rui-grey-700"
        placeholder="E.g. 0x9531c059098e3d194ff87febb587ab07b30b1306"
      />
    </label>
    <div class="p-3 pl-0">
      <RuiButton
        variant="outlined"
        color="primary"
        class="!p-3"
        @click="openDialog = true"
      >
        <RuiIcon
          name="lu-book-user"
          size="18"
        />
      </RuiButton>
    </div>
  </div>

  <RuiAlert
    v-if="connected && showWarning"
    type="warning"
    class="mt-2"
  >
    {{ t('trade.never_interacted') }}
  </RuiAlert>
  <RuiDialog
    v-model="openDialog"
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
        @click="openDialog = false"
      >
        <RuiIcon
          class="text-white"
          name="lu-x"
        />
      </RuiButton>
      <div class="flex flex-col max-h-[calc(100vh-400px)] overflow-auto">
        <div class="uppercase text-xs font-medium px-4 border-b border-default py-2 bg-rui-grey-50 dark:bg-rui-grey-900">
          {{ t('trade.recipient.tracked_addresses') }}
        </div>
        <div
          v-if="trackedAddresses.length === 0"
          class="p-4 text-rui-text-secondary"
        >
          {{ t('trade.recipient.no_addresses_found') }}
        </div>
        <template v-else>
          <TradeAddressDisplay
            v-for="address in trackedAddresses"
            :key="address"
            :address="address"
            :chain="chain"
            @click="select(address)"
          />
        </template>
        <div class="uppercase text-xs font-medium px-4 border-y border-default py-2 bg-rui-grey-50 dark:bg-rui-grey-900">
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
        <TradeAddressDisplay
          v-for="address in addressBookAddresses"
          :key="address"
          :address="address"
          :chain="chain"
          @click="select(address)"
        />
      </div>
    </RuiCard>
  </RuiDialog>
</template>
