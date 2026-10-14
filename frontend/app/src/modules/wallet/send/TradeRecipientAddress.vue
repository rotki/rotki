<script setup lang="ts">
import { useTemplateRef } from 'vue';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import TradeAddressDisplay from '@/modules/wallet/send/TradeAddressDisplay.vue';
import { useTradeRecipientAddress } from '@/modules/wallet/send/use-trade-recipient-address';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

const model = defineModel<string>({ required: true });

const { chain } = defineProps<{
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

const { getAddressName } = useAddressNameResolution();

/** The dialog's one search, matched against a tracked address and the name it resolves to. */
const searchTerm = computed<string>(() => get(modelAddressBookSearch).trim().toLowerCase());

const shownTracked = computed<string[]>(() => {
  const term = get(searchTerm);
  if (!term)
    return get(trackedAddresses);
  return get(trackedAddresses).filter(address => address.toLowerCase().includes(term)
    || (getAddressName(address, chain)?.toLowerCase().includes(term) ?? false));
});

/** An address book entry that is also a tracked account is listed once, under the tracked ones. */
const shownAddressBook = computed<string[]>(() => {
  const tracked = new Set(get(trackedAddresses).map(address => address.toLowerCase()));
  return get(filteredAddressBookOptions).filter(address => !tracked.has(address.toLowerCase()));
});

const { containerProps: trackedContainerProps, list: trackedList, wrapperProps: trackedWrapperProps } = useVirtualList(shownTracked, {
  itemHeight: 56,
});

const { containerProps: addressBookContainerProps, list: addressBookList, wrapperProps: addressBookWrapperProps } = useVirtualList(shownAddressBook, {
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
        class="h-16 flex items-center gap-2 px-3 bg-rui-grey-50 dark:bg-rui-grey-900 rounded-lg border border-default mt-1 duration-50 w-full"
        data-testid="recipient-field"
        :class="{
          'border-rui-error!': !valid,
        }"
      >
        <template v-if="model">
          <TradeAddressDisplay
            dense
            :chain="chain"
            :address="model"
            readonly
            class="flex-1 min-w-0"
          />
          <RuiTooltip
            v-if="connected && showWarning"
            :open-delay="200"
            :class-names="{ tooltip: 'max-w-64' }"
          >
            <template #activator>
              <RuiChip
                size="sm"
                variant="tonal"
                color="warning"
                class="shrink-0"
                data-testid="recipient-never-interacted"
              >
                {{ t('trade.recipient.new_address') }}
              </RuiChip>
            </template>
            {{ t('trade.never_interacted') }}
          </RuiTooltip>
          <RuiButton
            icon
            variant="text"
            size="sm"
            class="shrink-0"
            :aria-label="t('common.actions.clear')"
            data-testid="recipient-clear"
            @click="reset()"
          >
            <RuiIcon
              name="lu-x"
              size="16"
            />
          </RuiButton>
        </template>
        <template v-else>
          <label class="flex flex-col flex-1 min-w-0 gap-0.5">
            <span class="text-sm text-rui-text-secondary font-medium">
              {{ t('trade.to_address.label') }}
            </span>
            <input
              ref="searchInputRef"
              v-model="modelSearchValue"
              data-testid="recipient-search"
              type="text"
              class="outline-hidden w-full bg-transparent text-sm placeholder:text-rui-grey-400 dark:placeholder:text-rui-grey-700"
              placeholder="E.g. 0x9531c059098e3d194ff87febb587ab07b30b1306"
              @click="modelOpenSuggestionsMenu = true"
              @blur="applySearchInput()"
            />
          </label>
          <RuiTooltip
            :open-delay="400"
            class="shrink-0"
          >
            <template #activator>
              <RuiButton
                variant="text"
                color="primary"
                icon
                :aria-label="t('trade.recipient.select_recipient_address')"
                data-testid="recipient-open-address-book"
                @click="modelOpenOptionsDialog = true"
              >
                <RuiIcon
                  name="lu-book-user"
                  size="18"
                />
              </RuiButton>
            </template>
            {{ t('trade.recipient.select_recipient_address') }}
          </RuiTooltip>
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
        :aria-label="t('common.actions.close')"
        data-testid="recipient-dialog-close"
        @click="modelOpenOptionsDialog = false"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
      <div class="px-4 pt-3 pb-3 border-b border-default">
        <RuiTextField
          v-model="modelAddressBookSearch"
          prepend-icon="lu-search"
          dense
          hide-details
          color="primary"
          :label="t('common.actions.search')"
          label-placement="hidden"
          :placeholder="t('common.actions.search')"
          data-testid="recipient-dialog-search"
        />
      </div>
      <div class="flex flex-col h-[min(26rem,60vh)] overflow-hidden">
        <div
          v-if="shownTracked.length > 0"
          class="flex flex-1 flex-col relative overflow-hidden min-h-0"
        >
          <div class="text-xs font-medium text-rui-text-secondary px-4 border-b border-default py-2 bg-rui-grey-50 dark:bg-rui-grey-900">
            {{ t('trade.recipient.tracked_addresses') }}
          </div>
          <div
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
        <div
          v-if="shownAddressBook.length > 0"
          class="flex flex-1 flex-col overflow-hidden min-h-0"
          :class="{ 'border-t border-default': shownTracked.length > 0 }"
        >
          <div class="text-xs font-medium text-rui-text-secondary px-4 border-b border-default py-2 bg-rui-grey-50 dark:bg-rui-grey-900">
            {{ t('trade.recipient.from_private_address_book') }}
          </div>
          <div
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
        <div
          v-if="shownTracked.length === 0 && shownAddressBook.length === 0"
          class="flex-1 flex items-center justify-center text-sm text-rui-text-secondary"
          data-testid="recipient-dialog-empty"
        >
          {{ t('trade.recipient.no_addresses_found') }}
        </div>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
