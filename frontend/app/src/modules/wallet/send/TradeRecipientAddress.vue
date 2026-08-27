<script setup lang="ts">
import { useTemplateRef } from 'vue';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import TradeAddressDisplay from '@/modules/wallet/send/TradeAddressDisplay.vue';
import { useTradeRecipientAddress } from '@/modules/wallet/send/use-trade-recipient-address';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

const model = defineModel<string>({ required: true });

defineProps<{
  chain: string;
  showWarning: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const searchInputRef = useTemplateRef<InstanceType<typeof HTMLInputElement>>('searchInputRef');
const menuContainerRef = useTemplateRef<InstanceType<typeof HTMLDivElement>>('menuContainerRef');
const { focused: searchInputFocused } = useFocus(searchInputRef);
const { focused: menuFocusedWithin } = useFocusWithin(menuContainerRef);

const { connected } = storeToRefs(useWalletStore());

const {
  applySearchInput,
  directOptions,
  filteredAddressBookOptions,
  handleFocusChange,
  modelAddressBookSearch,
  modelOpenOptionsDialog,
  modelOpenSuggestionsMenu,
  modelSearchValue,
  reset,
  resolvingEns,
  select,
  trackedAddresses,
  valid,
} = useTradeRecipientAddress(model);

const anyFocused = logicOr(searchInputFocused, menuFocusedWithin);
const usedAnyFocused = useRefWithDebounce(anyFocused, 200);

watch(usedAnyFocused, (focused) => {
  handleFocusChange(focused);
});

const { containerProps: trackedContainerProps, list: trackedList, wrapperProps: trackedWrapperProps } = useVirtualList(trackedAddresses, {
  itemHeight: 56,
});

const { containerProps: addressBookContainerProps, list: addressBookList, wrapperProps: addressBookWrapperProps } = useVirtualList(filteredAddressBookOptions, {
  itemHeight: 56,
});
</script>

<template>
  <RuiMenu
    v-model="modelOpenSuggestionsMenu"
    :class-names="{ wrapper: 'w-full' }"
  >
    <template #activator>
      <div
        class="flex items-center bg-rui-grey-50 dark:bg-rui-grey-900 rounded-lg border border-default mt-1 duration-50 w-full"
        data-testid="recipient-field"
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
            data-testid="recipient-clear"
            @click="reset()"
          >
            <RuiIcon
              name="lu-x"
              size="18"
            />
          </RuiButton>
        </div>
        <template v-else>
          <label class="flex flex-col flex-1 p-3">
            <span class="text-sm text-rui-grey-500 font-medium block">
              {{ t('trade.to_address.label') }}
            </span>
            <input
              ref="searchInputRef"
              v-model="modelSearchValue"
              data-testid="recipient-search"
              type="text"
              class="outline-none w-full bg-transparent text-sm placeholder:text-rui-grey-400 dark:placeholder:text-rui-grey-700"
              placeholder="E.g. 0x9531c059098e3d194ff87febb587ab07b30b1306"
              @click="modelOpenSuggestionsMenu = true"
              @blur="applySearchInput()"
            />
          </label>
          <div class="p-3 pl-0">
            <RuiButton
              variant="outlined"
              color="primary"
              class="!p-3"
              data-testid="recipient-open-address-book"
              @click="modelOpenOptionsDialog = true"
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
    v-model="modelOpenOptionsDialog"
    max-width="500"
  >
    <RuiCard
      divide
      no-padding
      :class-names="{ content: 'overflow-hidden pb-2' }"
    >
      <template #header>
        {{ t('trade.recipient.select_recipient_address') }}
      </template>
      <RuiButton
        variant="text"
        class="absolute top-2 right-2"
        icon
        @click="modelOpenOptionsDialog = false"
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
              v-model="modelAddressBookSearch"
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
