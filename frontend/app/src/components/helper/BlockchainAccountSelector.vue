<template>
  <v-card v-bind="$attrs">
    <div :class="noPadding ? null : 'mx-4 pt-2'">
      <v-autocomplete
        :value="value"
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
        :open-on-clear="false"
        :label="label ? label : t('blockchain_account_selector.default_label')"
        :class="outlined ? 'blockchain-account-selector--outlined' : null"
        item-text="address"
        item-value="address"
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
                small
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

<script setup lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useTheme } from '@/composables/common';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';

const props = defineProps({
  label: { required: false, type: String, default: '' },
  hint: { required: false, type: Boolean, default: false },
  loading: { required: false, type: Boolean, default: false },
  usableAddresses: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  multiple: { required: false, type: Boolean, default: false },
  value: {
    required: false,
    type: [Object, Array] as PropType<GeneralAccount[] | GeneralAccount | null>,
    default: null
  },
  chains: {
    required: false,
    type: Array as PropType<Blockchain[]>,
    default: () => []
  },
  outlined: { required: false, type: Boolean, default: false },
  dense: { required: false, type: Boolean, default: false },
  noPadding: { required: false, type: Boolean, default: false },
  hideOnEmptyUsable: { required: false, type: Boolean, default: false }
});

const emit = defineEmits(['input']);

const { t } = useI18n();

const { chains, value, usableAddresses, hideOnEmptyUsable } = toRefs(props);
const search = ref('');
const { accounts } = storeToRefs(useAccountBalancesStore());
const selectableAccounts = computed(() => {
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

const displayedAccounts = computed(() => {
  const addresses = get(usableAddresses);
  const accounts = get(selectableAccounts);
  if (addresses.length > 0) {
    return accounts.filter(({ address }) => addresses.includes(address));
  }
  return get(hideOnEmptyUsable) ? [] : accounts;
});

const { ethNameSelector } = useEthNamesStore();

const filter = (item: GeneralAccount, queryText: string) => {
  const text = (get(ethNameSelector(item.address)) ?? '').toLowerCase();
  const address = item.address.toLocaleLowerCase();
  const query = queryText.toLocaleLowerCase();

  const labelMatches = text.indexOf(query) > -1;
  const addressMatches = address.indexOf(query) > -1;

  const tagMatches =
    item.tags
      .map(tag => tag.toLocaleLowerCase())
      .join(' ')
      .indexOf(query) > -1;

  return labelMatches || tagMatches || addressMatches;
};

const input = (value: string | null) => emit('input', value);

const { dark } = useTheme();
</script>

<style scoped lang="scss">
.blockchain-account-selector {
  &__list {
    &__item {
      max-width: 100%;
    }
  }

  :deep() {
    .v-select {
      &__selections {
        input {
          min-width: 0;
        }
      }
    }
  }
}
</style>
