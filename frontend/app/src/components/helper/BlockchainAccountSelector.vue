<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';

const props = withDefaults(
  defineProps<{
    label?: string;
    hint?: boolean;
    loading?: boolean;
    usableAddresses?: string[];
    multiple?: boolean;
    value: GeneralAccount[];
    chains: Blockchain[];
    outlined?: boolean;
    dense?: boolean;
    noPadding?: boolean;
    hideOnEmptyUsable?: boolean;
  }>(),
  {
    label: '',
    hint: false,
    loading: false,
    usableAddresses: () => [],
    multiple: false,
    chains: () => [],
    outlined: false,
    dense: false,
    noPadding: false,
    hideOnEmptyUsable: false
  }
);

const emit = defineEmits<{
  (e: 'input', value: GeneralAccount[]): void;
}>();

const { chains, value, usableAddresses, hideOnEmptyUsable, multiple } =
  toRefs(props);

const search = ref('');
const { t } = useI18n();

const { accounts } = storeToRefs(useAccountBalancesStore());

const internalValue = computed(() => {
  const accounts = get(value);
  if (get(multiple)) {
    return accounts;
  }

  if (!accounts) {
    return null;
  }
  if (accounts.length === 1) {
    return accounts[0];
  }
});

const selectableAccounts: ComputedRef<GeneralAccount[]> = computed(() => {
  const filteredChains = get(chains);
  const blockchainAccounts = get(accounts);
  if (filteredChains.length === 0) {
    return blockchainAccounts;
  }

  return blockchainAccounts.filter(({ chain }) =>
    filteredChains.includes(chain)
  );
});

const hintText = computed(() => {
  const all = t('blockchain_account_selector.all').toString();
  const selection = get(value);
  if (Array.isArray(selection)) {
    return selection.length > 0 ? selection.length.toString() : all;
  }
  return selection ? '1' : all;
});

const displayedAccounts: ComputedRef<GeneralAccount[]> = computed(() => {
  const addresses = get(usableAddresses);
  const accounts = get(selectableAccounts);
  if (addresses.length > 0) {
    return accounts.filter(({ address }) => addresses.includes(address));
  }
  return get(hideOnEmptyUsable) ? [] : accounts;
});

const { addressNameSelector } = useAddressesNamesStore();

const filter = (item: GeneralAccount, queryText: string) => {
  const text = (
    get(addressNameSelector(item.address, item.chain)) ?? ''
  ).toLowerCase();
  const address = item.address.toLocaleLowerCase();
  const query = queryText.toLocaleLowerCase();

  const labelMatches = text.includes(query);
  const addressMatches = address.includes(query);

  const tagMatches = item.tags
    .map(tag => tag.toLocaleLowerCase())
    .join(' ')
    .includes(query);

  return labelMatches || tagMatches || addressMatches;
};

const input = (value: null | GeneralAccount | GeneralAccount[]) => {
  if (Array.isArray(value)) {
    emit('input', value);
  } else {
    emit('input', value ? [value] : []);
  }
};

const { dark } = useTheme();

const getItemKey = (item: GeneralAccount) => item.address + item.chain;
</script>

<template>
  <v-card v-bind="$attrs">
    <div :class="noPadding ? null : 'mx-4 pt-2'">
      <v-autocomplete
        :value="internalValue"
        :items="displayedAccounts"
        :filter="filter"
        auto-select-first
        :search-input.sync="search"
        :multiple="multiple"
        :loading="loading"
        :disabled="loading"
        hide-details
        hide-selected
        :hide-no-data="!hideOnEmptyUsable"
        return-object
        chips
        single-line
        clearable
        :dense="dense"
        :outlined="outlined"
        :item-text="getItemKey"
        :open-on-clear="false"
        :label="label ? label : t('blockchain_account_selector.default_label')"
        :class="outlined ? 'blockchain-account-selector--outlined' : null"
        class="blockchain-account-selector"
        @input="input($event)"
      >
        <template #no-data>
          <span class="text-caption px-2">
            {{ t('blockchain_account_selector.no_data') }}
          </span>
        </template>
        <template #selection="data">
          <v-chip
            v-if="multiple"
            :key="data.item.chain + data.item.address"
            v-bind="data.attrs"
            :input-value="data.selected"
            :click="data.select"
            filter
            close
            close-label="overflow-x-hidden"
            @click:close="data.parent.selectItem(data.item)"
          >
            <account-display :account="data.item" />
          </v-chip>
          <div v-else class="overflow-x-hidden">
            <account-display :account="data.item" class="pr-2" />
          </div>
        </template>
        <template #item="data">
          <div
            class="blockchain-account-selector__list__item d-flex align-center justify-space-between flex-grow-1"
          >
            <div class="blockchain-account-selector__list__item__address-label">
              <v-chip
                :color="dark ? null : 'grey lighten-3'"
                filter
                class="text-truncate"
              >
                <account-display :account="data.item" />
              </v-chip>
            </div>
            <tag-display class="mb-1" :tags="data.item.tags" :small="true" />
          </div>
        </template>
      </v-autocomplete>
    </div>
    <v-card-text v-if="hint">
      {{ t('blockchain_account_selector.hint', { hintText }) }}
      <slot />
    </v-card-text>
  </v-card>
</template>

<style scoped lang="scss">
.blockchain-account-selector {
  &__list {
    &__item {
      max-width: 100%;
    }
  }

  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-select__selections) {
    padding: 2px;

    .v-chip {
      margin: 2px;
    }

    input {
      min-width: 0;
    }
  }

  /* stylelint-enable selector-class-pattern,selector-nested-pattern */
}
</style>
