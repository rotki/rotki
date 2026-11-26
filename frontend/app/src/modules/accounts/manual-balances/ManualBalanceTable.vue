<script setup lang="ts">
import type { ManualBalance, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import { type DataTableColumn, RuiButton, RuiDataTable, RuiIcon, type RuiIcons } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import ManualBalanceAssetCell from '@/modules/accounts/manual-balances/ManualBalanceAssetCell.vue';
import { useManualBalanceTable } from '@/modules/accounts/manual-balances/use-manual-balance-table';
import { useManualBalanceTableActions } from '@/modules/accounts/manual-balances/use-manual-balance-table-actions';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
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

const { deleteConfirm, deleteFailure, deleteRow, prepareForEdit, pricesLoading } = useManualBalanceTableActions();

const {
  clearFilters,
  emptyState,
  error,
  fields,
  filterByTag,
  filtered,
  loading,
  modelFilter: filters,
  modelPillParams: pillParams,
  pagination,
  pillLabels,
  sort,
  state,
} = useManualBalanceTable({ pricesLoading, type: () => type });

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
    <FailureStrip
      v-if="deleteFailure"
      class="m-3"
      :title="deleteFailure.title"
      :failure="deleteFailure.failure"
      data-testid="manual-balances-delete-error"
    />
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
        <ManualBalanceAssetCell
          :asset="row.asset"
          :asset-is-missing="row.assetIsMissing"
        />
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
          :delete-confirm="deleteConfirm"
          @edit-click="edit(row)"
          @delete-click="deleteRow(row.identifier)"
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
