<template>
  <card class="manual-balances" outlined-body :class="$style.table">
    <template #title>
      <refresh-button
        :loading="loading"
        :tooltip="tc('manual_balances_table.refresh.tooltip')"
        @refresh="refresh()"
      />
      <span>
        {{ title }}
      </span>
    </template>
    <template #actions>
      <v-row no-gutters justify="end">
        <v-col cols="12" md="6" lg="4">
          <tag-filter v-model="onlyTags" />
        </v-col>
      </v-row>
    </template>
    <data-table
      :loading="loading"
      :headers="headers"
      :items="visibleBalances"
      :item-class="getRowClass"
      class="manual-balances-list"
      sort-by="usdValue"
    >
      <template #item.label="{ item }">
        <div
          class="font-weight-medium"
          data-cy="label"
          :class="{
            'pt-0': !item.tags,
            [$style.label]: true
          }"
        >
          {{ item.label }}
        </div>
        <div>
          <tag-display :tags="item.tags" :small="true" />
        </div>
      </template>
      <template #item.asset="{ item }">
        <asset-details opens-details :asset="item.asset" />
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          v-if="item.usdPrice && item.usdPrice.gte(0)"
          show-currency="symbol"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdPrice"
        />
        <div v-else class="d-flex justify-end">
          <v-skeleton-loader width="70" type="text" />
        </div>
      </template>
      <template #item.amount="{ item }">
        <amount-display
          class="manual-balances-list__amount"
          :value="item.amount"
        />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :amount="item.amount"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdValue"
        />
      </template>
      <template #item.location="{ item }">
        <location-display
          class="manual-balances-list__location"
          :identifier="item.location"
          :data-cy="`manual-balances__location__${item.location}`"
        />
      </template>
      <template #item.actions="{ item }">
        <row-actions
          :edit-tooltip="tc('manual_balances_table.edit_tooltip')"
          :delete-tooltip="tc('manual_balances_table.delete_tooltip')"
          @edit-click="edit(item)"
          @delete-click="pendingDeletion = item.id"
        />
      </template>
      <template v-if="visibleBalances.length > 0" #body.append="{ isMobile }">
        <row-append
          label-colspan="5"
          :label="tc('common.total')"
          :is-mobile="isMobile"
          :right-patch-colspan="1"
        >
          <amount-display
            show-currency="symbol"
            class="manual-balances-list__amount"
            :fiat-currency="currencySymbol"
            :value="total"
          />
        </row-append>
      </template>
    </data-table>
    <confirm-dialog
      v-if="pendingDeletion !== null"
      display
      :title="tc('manual_balances_table.delete_dialog.title')"
      :message="tc('manual_balances_table.delete_dialog.message')"
      @cancel="pendingDeletion = null"
      @confirm="deleteBalance()"
    />
  </card>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';

import { aggregateTotal } from '@/filters';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { ManualBalance } from '@/types/manual-balances';
import { assert } from '@/utils/assertions';
import { One } from '@/utils/bignumbers';

const props = defineProps({
  title: { required: true, type: String },
  loading: { required: false, type: Boolean, default: false },
  balances: { required: true, type: Array as PropType<ManualBalance[]> }
});

const emit = defineEmits(['refresh', 'edit']);

const { t, tc } = useI18n();

const { balances } = toRefs(props);
const pendingDeletion = ref<number | null>(null);
const onlyTags = ref<string[]>([]);
const refresh = () => {
  emit('refresh');
};
const edit = (balance: ManualBalance) => {
  emit('edit', balance);
};

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { deleteManualBalance } = useManualBalancesStore();

const deleteBalance = async () => {
  const id = get(pendingDeletion);
  assert(id);
  set(pendingDeletion, null);
  await deleteManualBalance(id);
};

const { assetPrice } = useBalancePricesStore();

const visibleBalances = computed<ManualBalance[]>(() => {
  let mappedBalances = [];
  const selectedTags = get(onlyTags);
  if (selectedTags.length === 0) {
    mappedBalances = get(balances);
  } else {
    mappedBalances = get(balances).filter(balance => {
      const tags = balance.tags;
      if (tags) {
        return selectedTags.every(tag => tags.includes(tag));
      }
    });
  }

  return mappedBalances.map(item => ({
    ...item,
    usdPrice: get(assetPrice(item.asset))
  }));
});

const { exchangeRate } = useBalancePricesStore();

const total = computed(() => {
  return aggregateTotal(
    get(visibleBalances),
    get(currencySymbol),
    get(exchangeRate(get(currencySymbol))) ?? One
  );
});

const getRowClass = (item: ManualBalance) => {
  return `manual-balance__location__${item.location}`;
};

const headers = computed(() => [
  {
    text: t('common.location').toString(),
    value: 'location',
    align: 'center',
    width: '120px'
  },
  {
    text: t('manual_balances_table.columns.label').toString(),
    value: 'label'
  },
  {
    text: t('common.asset').toString(),
    value: 'asset',
    width: '200'
  },
  {
    text: t('common.price_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    value: 'usdPrice',
    align: 'end'
  },
  {
    text: t('common.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    value: 'usdValue',
    align: 'end'
  },
  {
    text: t('manual_balances_table.columns.actions').toString(),
    value: 'actions',
    align: 'center',
    sortable: false,
    width: '50'
  }
]);
</script>

<style module lang="scss">
.label {
  padding-bottom: 0 !important;
}

.table {
  :global {
    th {
      &:first-child {
        span {
          padding-left: 16px;
        }
      }
    }
  }
}
</style>
