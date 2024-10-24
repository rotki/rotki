<script setup lang="ts">
import { objectOmit } from '@vueuse/shared';
import { isEqual } from 'lodash-es';
import { Section } from '@/types/status';
import type { Filters, Matcher } from '@/composables/filters/manual-balances';
import type { ManualBalance, ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/types/manual-balances';
import type { DataTableColumn } from '@rotki/ui-library';

const props = defineProps<{
  title: string;
  type: 'liabilities' | 'balances';
}>();

const emit = defineEmits<{
  (e: 'refresh'): void;
  (e: 'edit', value: ManualBalance): void;
}>();

const { t } = useI18n();

const tags = ref<string[]>([]);
const refreshing = ref(false);

const store = useManualBalancesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { manualBalances, manualLiabilities } = storeToRefs(store);
const { fetchLiabilities, fetchBalances, fetchManualBalances, deleteManualBalance } = store;
const { isLoading } = useStatusStore();

const dataSource = computed(() => (props.type === 'liabilities' ? get(manualLiabilities) : get(manualBalances)));

const locations = computed(() =>
  [
    ...get(manualBalances).map(item => item.location),
    ...get(manualLiabilities).map(item => item.location),
  ].filter(
    uniqueStrings,
  ),
);

const {
  isLoading: loading,
  filters,
  matchers,
  state,
  fetchData,
  pagination,
  sort,
} = usePaginationFilters<
  ManualBalanceWithPrice,
  ManualBalanceRequestPayload,
  Filters,
  Matcher
>(
  payload => (props.type === 'liabilities' ? fetchLiabilities(payload) : fetchBalances(payload)),
  {
    history: 'router',
    filterSchema: () => useManualBalanceFilter(locations),
    extraParams: computed(() => ({
      tags: get(tags),
    })),
    defaultSortBy: [{
      column: 'value',
      direction: 'desc',
    }],
    onUpdateFilters(query) {
      const schema = ManualBalancesFilterSchema.parse(query);
      if (schema.tags)
        set(tags, schema.tags);
    },
  },
);

async function refresh() {
  set(refreshing, true);
  await fetchManualBalances(true);
  set(refreshing, false);
}

function edit(balance: ManualBalanceWithPrice) {
  emit('edit', objectOmit(balance, ['value', 'price']));
}

function getRowClass(item: ManualBalance) {
  return `manual-balance__location__${item.location}`;
}

const cols = computed<DataTableColumn<ManualBalanceWithPrice>[]>(() => [
  {
    label: t('common.location'),
    key: 'location',
    align: 'center',
    class: 'w-[120px]',
    cellClass: 'py-2 w-[120px]',
  },
  {
    label: t('common.label'),
    key: 'label',
    sortable: true,
  },
  {
    label: t('common.asset'),
    key: 'asset',
    sortable: true,
    class: 'w-[12rem] xl:w-[16rem] 2xl:w-[20rem]',
  },
  {
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol),
    }),
    key: 'price',
    sortable: true,
    align: 'end',
  },
  {
    label: t('common.amount'),
    key: 'amount',
    sortable: true,
    align: 'end',
  },
  {
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    key: 'usdValue',
    sortable: true,
    align: 'end',
  },
  {
    label: t('common.actions_text'),
    key: 'actions',
    align: 'end',
    class: 'w-[120px]',
    cellClass: 'w-[120px]',
  },
]);

const { show } = useConfirmStore();

function showDeleteConfirmation(id: number) {
  show(
    {
      title: t('manual_balances_table.delete_dialog.title'),
      message: t('manual_balances_table.delete_dialog.message'),
    },
    () => deleteManualBalance(id),
  );
}

watchImmediate(dataSource, async (newBalances, oldBalances) => {
  if (isEqual(newBalances, oldBalances))
    return;

  await fetchData();
});

watchDebounced(
  isLoading(Section.PRICES),
  async (isLoading, wasLoading) => {
    if (!isLoading && wasLoading)
      await fetchData();
  },
  { debounce: 800, maxWait: 1000 },
);
</script>

<template>
  <RuiCard class="manual-balances">
    <template #custom-header>
      <div class="px-4 pt-4">
        <div class="flex flex-row items-center flex-wrap gap-3">
          <RefreshButton
            :loading="refreshing"
            :tooltip="t('manual_balances_table.refresh.tooltip')"
            @refresh="refresh()"
          />
          <span class="text-h6">
            {{ title }}
          </span>
          <div class="grow" />
          <div class="flex flex-col sm:flex-row flex-1 gap-2 min-w-full md:min-w-[40rem]">
            <TagFilter
              v-model="tags"
              class="w-full flex-1"
              hide-details
            />
            <TableFilter
              v-model:matches="filters"
              class="w-full flex-1"
              :matchers="matchers"
            />
          </div>
        </div>
      </div>
    </template>
    <RuiDataTable
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      outlined
      dense
      :loading="loading"
      :cols="cols"
      row-attr="label"
      :rows="state.data"
      :item-class="getRowClass"
      class="manual-balances-list lg:[&_table]:w-full"
    >
      <template #item.label="{ row }">
        <div
          class="font-medium !pb-0 text-truncate min-w-[8rem] max-w-[16rem]"
          :title="row.label"
          data-cy="label"
          :class="{
            'pt-0': !row.tags,
          }"
        >
          {{ row.label }}
        </div>
        <div v-if="row.tags">
          <TagDisplay
            :tags="row.tags"
            :small="true"
          />
        </div>
      </template>
      <template #item.asset="{ row }">
        <AssetDetails
          class="[&>div]:max-w-[12rem] xl:[&>div]:max-w-[16rem] 2xl:[&>div]:max-w-[20rem]"
          opens-details
          :asset="row.asset"
        />
      </template>
      <template #item.price="{ row }">
        <AmountDisplay
          :loading="!row.price || row.price.lt(0)"
          no-scramble
          show-currency="symbol"
          :price-asset="row.asset"
          :price-of-asset="row.price"
          :value="row.price"
        />
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay
          data-cy="manual-balances__amount"
          :value="row.amount"
        />
      </template>
      <template #item.value="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="row.asset"
          :price-of-asset="row.price"
          :fiat-currency="currencySymbol"
          :value="row.value"
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
          align="end"
          :edit-tooltip="t('manual_balances_table.edit_tooltip')"
          :delete-tooltip="t('manual_balances_table.delete_tooltip')"
          @edit-click="edit(row)"
          @delete-click="showDeleteConfirmation(row.identifier)"
        />
      </template>
      <template
        v-if="state.data.length > 0"
        #body.append
      >
        <RowAppend
          :label-colspan="5"
          :right-patch-colspan="1"
        >
          <template #label>
            <span class="p-4">
              {{ t('common.total') }}
            </span>
          </template>

          <AmountDisplay
            v-if="state.totalUsdValue"
            show-currency="symbol"
            class="p-4"
            :fiat-currency="currencySymbol"
            data-cy="manual-balances__amount"
            :value="state.totalUsdValue"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
