<script setup lang="ts">
import type { DataTableColumn, RuiIcons } from '@rotki/ui-library';
import type { ManualBalance, ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import { isEqual } from 'es-toolkit';
import { type Filters, manualBalanceTagsParams } from '@/modules/accounts/manual-balances/manual-balance-filter-keys';
import ManualBalanceMissingAssetWarning
  from '@/modules/accounts/manual-balances/ManualBalanceMissingAssetWarning.vue';
import { useManualBalanceFields } from '@/modules/accounts/manual-balances/use-manual-balance-fields';
import { useManualBalanceTableActions } from '@/modules/accounts/manual-balances/use-manual-balance-table-actions';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useManualBalancesOrLiabilities } from '@/modules/balances/manual/use-manual-balances-or-liabilities';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable, useTableEmptyState } from '@/modules/core/table/use-server-table';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

const { type } = defineProps<{
  type: 'liabilities' | 'balances';
}>();

const emit = defineEmits<{
  edit: [value: ManualBalance];
  add: [];
}>();

defineSlots<{
  /** Controls placed ahead of the filter in the table's toolbar. */
  toolbar?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const tags = ref<string[]>([]);

const { pillParams, source: tagsSource } = manualBalanceTagsParams(tags);

const { dataSource, fetch, locations } = useManualBalancesOrLiabilities(() => type);
const { prepareForEdit, pricesLoading, showDeleteConfirmation } = useManualBalanceTableActions();

const modelFilters = ref<Filters>({});
const fields = useManualBalanceFields(locations, modelFilters);
const pillLabels = usePillBarLabels();

const {
  collection: state,
  error,
  filter: filters,
  isLoading: loading,
  pagination,
  refetch: fetchData,
  sort,
} = useServerTable<
  ManualBalanceWithPrice,
  ManualBalanceRequestPayload,
  Filters
>({
  fetch,
  fields,
  filters: modelFilters,
  params: [tagsSource],
  sort: {
    default: [
      {
        column: 'value',
        direction: 'desc',
      },
    ],
  },
  urlState: { mode: 'route' },
});

const emptyState = useTableEmptyState({ error });

const filtered = computed<boolean>(() => get(tags).length > 0 || Object.values(get(filters)).some(value => value !== undefined && value !== ''));

/** An empty table says whether the filters hid every entry or there are none yet, and offers the way out. */
const emptyNotice = computed<{ icon: RuiIcons; title: string; description: string }>(() => {
  if (get(filtered)) {
    return {
      description: t('manual_balances_table.empty.filtered_description'),
      icon: 'lu-search-x',
      title: t('manual_balances_table.empty.filtered_title'),
    };
  }
  return type === 'liabilities'
    ? {
        description: t('manual_balances_table.empty.liabilities_description'),
        icon: 'lu-hand-coins',
        title: t('manual_balances_table.empty.liabilities_title'),
      }
    : {
        description: t('manual_balances_table.empty.balances_description'),
        icon: 'lu-notebook-pen',
        title: t('manual_balances_table.empty.balances_title'),
      };
});

function clearFilters(): void {
  set(filters, {});
  set(tags, []);
}

/** A tag in a row narrows the table to that tag, the same as picking it in the filter bar. */
function filterByTag(tag: string): void {
  if (!get(tags).includes(tag))
    set(tags, [...get(tags), tag]);
}

function edit(balance: ManualBalanceWithPrice): void {
  emit('edit', prepareForEdit(balance));
}

// the label takes the width the table has left; the other columns size to their content
const cols = computed<DataTableColumn<ManualBalanceWithPrice>[]>(() => [{
  class: 'w-full',
  key: 'label',
  label: t('common.label'),
  sortable: true,
}, {
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  cellClass: 'whitespace-nowrap',
  key: 'location',
  label: t('common.location'),
}, {
  align: 'end',
  // like the other balance tables: the price recedes and the value leads
  cellClass: 'text-rui-text-secondary',
  key: 'price',
  label: t('common.price'),
  sortable: true,
}, {
  align: 'end',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'font-medium',
  key: 'value',
  label: t('common.value'),
  sortable: true,
}, {
  align: 'end',
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
  <TableFrame>
    <template #toolbar>
      <slot name="toolbar" />
      <PillFilterBar
        v-model:matches="filters"
        v-model:params="pillParams"
        class="flex-1 min-w-64"
        :fields="fields"
        :labels="pillLabels"
      />
    </template>
    <RuiDataTable
      v-model:sort.external="sort"
      v-model:pagination.external="pagination"
      dense
      :loading="loading"
      :cols="cols"
      :empty="emptyState"
      row-attr="label"
      :rows="state.data"
      data-testid="manual-balances"
      class="bg-rui-surface"
    >
      <template #item.label="{ row }">
        <div
          class="font-medium truncate min-w-32 max-w-112"
          :title="row.label"
          data-testid="label"
        >
          {{ row.label }}
        </div>
        <div v-if="row.tags">
          <TagDisplay
            :tags="row.tags"
            small
            clickable
            @select="filterByTag($event)"
          />
        </div>
      </template>
      <template #item.asset="{ row }">
        <AssetDetails
          v-if="!row.assetIsMissing"
          class="[&>div]:max-w-48 xl:[&>div]:max-w-64 2xl:[&>div]:max-w-80"
          :asset="row.asset"
          :actions="{ hideActions: true }"
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
          data-testid="manual-balance-amount"
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
          horizontal
          size="20px"
          data-testid="manual-balance-location"
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
          :label="t('common.total')"
          :right-patch-colspan="1"
        >
          <FiatDisplay
            v-if="state.totalValue"
            class="font-bold"
            data-testid="manual-balance-total"
            :value="state.totalValue"
          />
        </RowAppend>
      </template>
      <template
        v-if="!error"
        #no-data
      >
        <TableEmptyNotice
          :icon="emptyNotice.icon"
          :title="emptyNotice.title"
          :description="emptyNotice.description"
          :data-testid="filtered ? 'manual-balances-empty-filtered' : 'manual-balances-empty'"
        >
          <RuiButton
            v-if="filtered"
            variant="outlined"
            color="primary"
            data-testid="manual-balances-empty-clear-filters"
            @click="clearFilters()"
          >
            {{ t('manual_balances_table.empty.clear_filters') }}
          </RuiButton>
          <RuiButton
            v-else
            color="primary"
            data-testid="manual-balances-empty-add"
            @click="emit('add')"
          >
            <template #prepend>
              <RuiIcon name="lu-plus" />
            </template>
            {{ type === 'liabilities' ? t('manual_balances_table.empty.add_liability') : t('manual_balances.add_manual_balance') }}
          </RuiButton>
        </TableEmptyNotice>
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
