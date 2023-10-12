<script setup lang="ts">
import { type ManualBalance } from '@/types/manual-balances';
import type {
  DataTableColumn,
  DataTableSortColumn
} from '@rotki/ui-library-compat';

const props = withDefaults(
  defineProps<{
    title: string;
    balances: ManualBalance[];
    loading?: boolean;
  }>(),
  { loading: false }
);

const emit = defineEmits<{
  (e: 'refresh'): void;
  (e: 'edit', value: ManualBalance): void;
}>();

const { t } = useI18n();

const { balances } = toRefs(props);

const onlyTags = ref<string[]>([]);
const sort = ref<DataTableSortColumn>({
  column: 'usdValue',
  direction: 'desc'
});

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

const cols = computed<DataTableColumn[]>(() => [
  {
    label: t('common.location'),
    key: 'location',
    align: 'start',
    width: '120px'
  },
  {
    label: t('manual_balances_table.columns.label'),
    key: 'label'
  },
  {
    label: t('common.asset'),
    key: 'asset',
    sortable: true,
    width: '200'
  },
  {
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol)
    }),
    key: 'usdPrice',
    sortable: true,
    align: 'end'
  },
  {
    label: t('common.amount'),
    key: 'amount',
    sortable: true,
    align: 'end'
  },
  {
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }),
    key: 'usdValue',
    sortable: true,
    align: 'end'
  },
  {
    label: t('manual_balances_table.columns.actions'),
    key: 'actions',
    align: 'start',
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
  <RuiCard class="manual-balances">
    <template #custom-header>
      <div class="px-4 pt-4">
        <div class="flex flex-row items-center flex-wrap">
          <RefreshButton
            :loading="loading"
            :tooltip="t('manual_balances_table.refresh.tooltip')"
            @refresh="refresh()"
          />
          <span class="text-h6">
            {{ title }}
          </span>
          <div class="grow" />
          <TagFilter v-model="onlyTags" class="max-w-sm" hide-details />
        </div>
      </div>
    </template>
    <RuiDataTable
      outlined
      :loading="loading"
      :cols="cols"
      :rows="visibleBalances"
      :sort="sort"
      :item-class="getRowClass"
      class="manual-balances-list"
      sort-by="usdValue"
      @update:sort="sort = $event"
    >
      <template #item.label="{ row }">
        <div
          class="font-medium"
          data-cy="label"
          :class="{
            'pt-0': !row.tags,
            '!pb-0': true
          }"
        >
          {{ row.label }}
        </div>
        <div>
          <TagDisplay :tags="row.tags" :small="true" />
        </div>
      </template>
      <template #item.asset="{ row }">
        <AssetDetails opens-details :asset="row.asset" />
      </template>
      <template #item.usdPrice="{ row }">
        <AmountDisplay
          v-if="row.usdPrice && row.usdPrice.gte(0)"
          no-scramble
          show-currency="symbol"
          :price-asset="row.asset"
          :price-of-asset="row.usdPrice"
          fiat-currency="USD"
          :value="row.usdPrice"
        />
        <div v-else class="flex justify-end">
          <VSkeletonLoader width="70" type="text" />
        </div>
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay data-cy="manual-balances__amount" :value="row.amount" />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="row.asset"
          :price-of-asset="row.usdPrice"
          fiat-currency="USD"
          :value="row.usdValue"
        />
      </template>
      <template #item.location="{ row }">
        <LocationDisplay
          :identifier="row.location"
          data-cy="manual-balances__location"
        />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          :edit-tooltip="t('manual_balances_table.edit_tooltip')"
          :delete-tooltip="t('manual_balances_table.delete_tooltip')"
          @edit-click="edit(row)"
          @delete-click="showDeleteConfirmation(row.id)"
        />
      </template>
      <template v-if="visibleBalances.length > 0" #body.append>
        <RowAppend :label-colspan="5" :right-patch-colspan="1">
          <template #label>
            <span class="p-4">
              {{ t('common.total') }}
            </span>
          </template>

          <AmountDisplay
            show-currency="symbol"
            class="p-4"
            :fiat-currency="currencySymbol"
            data-cy="manual-balances__amount"
            :value="total"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
