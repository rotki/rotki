<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { ManualBalance, ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import { isEqual } from 'es-toolkit';
import ManualBalanceMissingAssetWarning
  from '@/modules/accounts/manual-balances/ManualBalanceMissingAssetWarning.vue';
import { useManualBalanceTableActions } from '@/modules/accounts/manual-balances/use-manual-balance-table-actions';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useManualBalancesOrLiabilities } from '@/modules/balances/manual/use-manual-balances-or-liabilities';
import { type Filters, ManualBalancesFilterSchema, type Matcher, useManualBalanceFilter } from '@/modules/core/table/filters/use-manual-balances-filter';
import TableFilter from '@/modules/core/table/TableFilter.vue';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import TagFilter from '@/modules/shell/components/inputs/TagFilter.vue';
import RefreshButton from '@/modules/shell/components/RefreshButton.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

const { type } = defineProps<{
  type: 'liabilities' | 'balances';
}>();

const emit = defineEmits<{
  edit: [value: ManualBalance];
}>();

const { t } = useI18n({ useScope: 'global' });

const tags = ref<string[]>([]);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { dataSource, fetch, locations } = useManualBalancesOrLiabilities(() => type);
const { prepareForEdit, pricesLoading, refresh, refreshing, showDeleteConfirmation } = useManualBalanceTableActions();

const {
  fetchData,
  filters,
  isLoading: loading,
  matchers,
  pagination,
  sort,
  state,
} = usePaginationFilters<
  ManualBalanceWithPrice,
  ManualBalanceRequestPayload,
  Filters,
  Matcher
>(fetch, {
  defaultSortBy: [
    {
      column: 'value',
      direction: 'desc',
    },
  ],
  extraParams: computed(() => ({
    tags: get(tags),
  })),
  filterSchema: () => useManualBalanceFilter(locations),
  history: 'router',
  onUpdateFilters(query) {
    const schema = ManualBalancesFilterSchema.parse(query);
    if (schema.tags)
      set(tags, schema.tags);
  },
});

function edit(balance: ManualBalanceWithPrice): void {
  emit('edit', prepareForEdit(balance));
}

function getRowClass(item: ManualBalance) {
  return `manual-balance__location__${item.location}`;
}

const cols = computed<DataTableColumn<ManualBalanceWithPrice>[]>(() => [{
  align: 'center',
  cellClass: 'py-2 w-[120px]',
  class: 'w-[120px]',
  key: 'location',
  label: t('common.location'),
}, {
  key: 'label',
  label: t('common.label'),
  sortable: true,
}, {
  class: 'w-[12rem] xl:w-[16rem] 2xl:w-[20rem]',
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  align: 'end',
  key: 'price',
  label: t('common.price_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}, {
  align: 'end',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  key: 'value',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'w-[120px]',
  class: 'w-[120px]',
  key: 'actions',
  label: t('common.actions_text'),
}]);

useRememberTableSorting<ManualBalanceWithPrice>(TableId.MANUAL_BALANCES, sort, cols);

watchImmediate(dataSource, async (newBalances, oldBalances) => {
  if (isEqual(newBalances, oldBalances))
    return;

  await fetchData();
});

watchDebounced(
  pricesLoading,
  async (isLoading, wasLoading) => {
    if (!isLoading && wasLoading)
      await fetchData();
  },
  { debounce: 800, maxWait: 1000 },
);
</script>

<template>
  <RuiCard data-cy="manual-balances">
    <template #custom-header>
      <div class="px-4 pt-4">
        <div class="flex flex-row items-center flex-wrap gap-3">
          <RefreshButton
            :loading="refreshing"
            :tooltip="t('manual_balances_table.refresh.tooltip')"
            @refresh="refresh()"
          />
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
      data-cy="manual-balances"
      class="lg:[&_table]:w-full"
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
          v-if="!row.assetIsMissing"
          hide-actionsusd-pr
          class="[&>div]:max-w-[12rem] xl:[&>div]:max-w-[16rem] 2xl:[&>div]:max-w-[20rem]"
          :asset="row.asset"
        />
        <ManualBalanceMissingAssetWarning v-else />
      </template>
      <template #item.price="{ row }">
        <FiatDisplay
          v-if="!row.assetIsMissing"
          :loading="!row.price || row.price.lt(0)"
          :value="row.price"
          :price-asset="row.asset"
        />
        <template v-else>
          -
        </template>
      </template>
      <template #item.amount="{ row }">
        <ValueDisplay
          data-cy="manual-balances__amount"
          :value="row.amount"
        />
      </template>
      <template #item.value="{ row }">
        <AssetValueDisplay
          v-if="!row.assetIsMissing"
          :asset="row.asset"
          :value="row.value"
        />
        <template v-else>
          -
        </template>
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

          <FiatDisplay
            v-if="state.totalValue"
            class="p-4"
            data-cy="manual-balances__amount"
            :value="state.totalValue"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
