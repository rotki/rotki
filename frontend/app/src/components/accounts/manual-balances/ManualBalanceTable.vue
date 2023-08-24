<script setup lang="ts">
import { type PropType } from 'vue';
import { type ManualBalance } from '@/types/manual-balances';

const props = defineProps({
  title: { required: true, type: String },
  loading: { required: false, type: Boolean, default: false },
  balances: { required: true, type: Array as PropType<ManualBalance[]> }
});

const emit = defineEmits(['refresh', 'edit']);

const { t } = useI18n();

const { balances } = toRefs(props);
const onlyTags = ref<string[]>([]);
const refresh = () => {
  emit('refresh');
};
const edit = (balance: ManualBalance) => {
  emit('edit', balance);
};

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { deleteManualBalance } = useManualBalancesStore();

const { assetPrice } = useBalancePricesStore();

const visibleBalances = computed<ManualBalance[]>(() => {
  let mappedBalances: ManualBalance[];
  const selectedTags = get(onlyTags);
  if (selectedTags.length === 0) {
    mappedBalances = get(balances);
  } else {
    mappedBalances = get(balances).filter(balance => {
      const tags = balance.tags ?? [];
      return selectedTags.every(tag => tags.includes(tag));
    });
  }

  return mappedBalances.map(item => ({
    ...item,
    usdPrice: get(assetPrice(item.asset))
  }));
});

const { exchangeRate } = useBalancePricesStore();

const total = computed(() =>
  aggregateTotal(
    get(visibleBalances),
    get(currencySymbol),
    get(exchangeRate(get(currencySymbol))) ?? One
  )
);

const getRowClass = (item: ManualBalance) =>
  `manual-balance__location__${item.location}`;

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

const { show } = useConfirmStore();

const showDeleteConfirmation = (id: number) => {
  show(
    {
      title: t('manual_balances_table.delete_dialog.title'),
      message: t('manual_balances_table.delete_dialog.message')
    },
    () => deleteManualBalance(id)
  );
};
</script>

<template>
  <Card class="manual-balances" :class="$style.table">
    <template #title>
      <RefreshButton
        :loading="loading"
        :tooltip="t('manual_balances_table.refresh.tooltip')"
        @refresh="refresh()"
      />
      <span>
        {{ title }}
      </span>
    </template>
    <template #actions>
      <VRow no-gutters justify="end">
        <VCol cols="12" md="6" lg="4">
          <TagFilter v-model="onlyTags" />
        </VCol>
      </VRow>
    </template>
    <DataTable
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
          <TagDisplay :tags="item.tags" :small="true" />
        </div>
      </template>
      <template #item.asset="{ item }">
        <AssetDetails opens-details :asset="item.asset" />
      </template>
      <template #item.usdPrice="{ item }">
        <AmountDisplay
          v-if="item.usdPrice && item.usdPrice.gte(0)"
          no-scramble
          show-currency="symbol"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdPrice"
        />
        <div v-else class="d-flex justify-end">
          <VSkeletonLoader width="70" type="text" />
        </div>
      </template>
      <template #item.amount="{ item }">
        <AmountDisplay
          class="manual-balances-list__amount"
          :value="item.amount"
        />
      </template>
      <template #item.usdValue="{ item }">
        <AmountDisplay
          show-currency="symbol"
          :amount="item.amount"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdValue"
        />
      </template>
      <template #item.location="{ item }">
        <LocationDisplay
          class="manual-balances-list__location"
          :identifier="item.location"
          :data-cy="`manual-balances__location__${item.location}`"
        />
      </template>
      <template #item.actions="{ item }">
        <RowActions
          :edit-tooltip="t('manual_balances_table.edit_tooltip')"
          :delete-tooltip="t('manual_balances_table.delete_tooltip')"
          @edit-click="edit(item)"
          @delete-click="showDeleteConfirmation(item.id)"
        />
      </template>
      <template v-if="visibleBalances.length > 0" #body.append="{ isMobile }">
        <RowAppend
          label-colspan="5"
          :label="t('common.total')"
          :is-mobile="isMobile"
          :right-patch-colspan="1"
        >
          <AmountDisplay
            show-currency="symbol"
            class="manual-balances-list__amount"
            :fiat-currency="currencySymbol"
            :value="total"
          />
        </RowAppend>
      </template>
    </DataTable>
  </Card>
</template>

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
