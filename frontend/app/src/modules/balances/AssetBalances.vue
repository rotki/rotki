<script setup lang="ts">
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AssetBreakdownOptions } from '@/modules/balances/types/balances';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { isEvmNativeToken } from '@/modules/assets/types';
import { useAssetBalanceSearch } from '@/modules/assets/use-asset-balance-search';
import { useAssetSelectInfo } from '@/modules/assets/use-asset-select-info';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import { useValuePending } from '@/modules/balances/value-pending';
import { bigNumberSum, calculatePercentage } from '@/modules/core/common/data/calculation';
import { hasAwaitingClaim, sortAssetBalances } from '@/modules/core/common/display/balances';
import { TableColumn } from '@/modules/core/table/table-column';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useTableRowWindow, useWindowedSelectAll } from '@/modules/core/table/use-table-row-window';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

defineOptions({
  name: 'AssetBalances',
});

const search = defineModel<string>('search', { default: '', required: false });
const selected = defineModel<string[] | undefined>('selected', { required: false });

const {
  balances,
  breakdown,
  layout,
  loading = false,
  selectionMode = false,
  showPerProtocol = false,
  stickyHeader = false,
  visibleColumns = [],
} = defineProps<{
  balances: AssetBalanceWithPrice[];
  breakdown?: AssetBreakdownOptions;
  loading?: boolean;
  stickyHeader?: boolean;
  visibleColumns?: TableColumn[];
  showPerProtocol?: boolean;
  selectionMode?: boolean;
  /**
   * Where the table sits, when not on a page of its own.
   *
   * @remarks
   * `nested`: inside another table's expanded row. It follows that table's column style and leaves the
   * total out, since the row it expands already shows it. `panel`: the same, filling a panel that
   * scrolls on its own, so it lists every row without an outline or a footer. Under a panel that
   * provides its scroller, only the rows in view render.
   */
  layout?: 'nested' | 'panel';
}>();

defineSlots<{
  /** What the table says when it has no rows and no search is narrowing it. */
  empty?: () => any;
}>();

const nested = computed<boolean>(() => layout !== undefined);

const fillsPanel = computed<boolean>(() => layout === 'panel');

const { t } = useI18n({ useScope: 'global' });
const expanded = ref<AssetBalanceWithPrice[]>([]);

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'value',
  direction: 'desc' as const,
});

const debouncedSearch = refDebounced(search, 200);

const { getAssetInfo } = useAssetSelectInfo();
const { matches, prioritizeExactMatches } = useAssetBalanceSearch(() => balances, debouncedSearch);
const statistics = useStatisticsStore();
const { totalNetWorth } = storeToRefs(statistics);
const { isTotalPending, isValuePending } = useValuePending();
const { isMdAndDown } = useBreakpoint();

const isExpanded = (asset: string): boolean => get(expanded).some(row => row.asset === asset);

function shouldShowRowExpander(row: AssetBalanceWithPrice): boolean {
  const hasBreakdown = Boolean(row.breakdown);
  const shouldShowNativeBreakdown = (!breakdown?.hide && isEvmNativeToken(row.asset)) ?? false;
  const hasPerProtocolDetails = row.perProtocol?.some(hasAwaitingClaim) || (row.perProtocol && row.perProtocol.length > 1) || false;
  return hasBreakdown || shouldShowNativeBreakdown || hasPerProtocolDetails;
}

function expand(item: AssetBalanceWithPrice) {
  set(expanded, isExpanded(item.asset) ? [] : [item]);
}

const total = computed<BigNumber>(() => bigNumberSum(get(matches).map(({ value }) => value)));

const totalPending = computed<boolean>(() => isTotalPending(get(matches)));

function percentageOfTotalNetValue(val: BigNumber): string {
  return calculatePercentage(val, get(totalNetWorth));
}

function percentageOfCurrentGroup(val: BigNumber): string {
  return calculatePercentage(val, get(total));
}

/**
 * Fixed widths, so panel tables stacked one under another keep their columns in line.
 *
 * @remarks
 * They only hold while the asset column is the one auto-width column: a `w-full` there claims the
 * spare width and the browser shrinks the fixed columns back to their content.
 */
const PANEL_COLUMN_WIDTHS: Record<string, string> = {
  amount: 'w-28',
  asset: '',
  perProtocol: 'w-20',
  price: 'w-28',
  value: 'w-32',
};

/** Columns a panel drops when the screen is too narrow for them, so Amount and Value stay in view. */
const NARROW_PANEL_DROPPED = new Set<string>(['perProtocol', 'price']);

/** The panel variant of the columns: fixed widths, and fewer of them on a narrow screen. */
function panelColumns(headers: DataTableColumn<AssetBalanceWithPrice>[]): DataTableColumn<AssetBalanceWithPrice>[] {
  return headers
    .filter(header => !get(isMdAndDown) || !NARROW_PANEL_DROPPED.has(String(header.key)))
    .map((header) => {
      const width = PANEL_COLUMN_WIDTHS[String(header.key)];
      if (width === undefined)
        return header;

      const rest = (header.class ?? '').split(' ').filter(name => name !== 'w-full');
      const shrinks = header.key === 'asset' ? { cellClass: [header.cellClass, 'max-w-0 overflow-hidden'].filter(Boolean).join(' ') } : {};
      return { ...header, ...shrinks, class: [...rest, width].filter(Boolean).join(' ') };
    });
}

const tableHeaders = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => {
  const headers: DataTableColumn<AssetBalanceWithPrice>[] = [{
    cellClass: 'py-0',
    class: 'text-no-wrap w-full',
    key: 'asset',
    label: t('common.asset'),
    sortable: true,
  }, {
    align: 'end',
    // like the dashboard's asset table: the price recedes and the value leads
    cellClass: 'py-0 text-rui-text-secondary',
    key: 'price',
    label: t('common.price'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0 font-medium',
    class: 'text-no-wrap',
    key: 'value',
    label: t('common.value'),
    sortable: true,
  }];

  if (showPerProtocol) {
    headers.splice(1, 0, {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'perProtocol',
      label: t('common.location'),
      sortable: false,
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0 text-rui-text-secondary',
      class: 'text-no-wrap',
      key: 'percentageOfTotalNetValue',
      label: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
    });
  }

  if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0 text-rui-text-secondary',
      class: 'text-no-wrap',
      key: 'percentageOfTotalCurrentGroup',
      label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group: t('blockchain_balances.group_label'),
      }),
    });
  }

  return get(fillsPanel) ? panelColumns(headers) : headers;
});

const rowAppendLabelColspan = computed(() => {
  let colspan = 3;

  if (selectionMode)
    colspan++;
  if (showPerProtocol)
    colspan++;

  return colspan;
});

useRememberTableSorting<AssetBalanceWithPrice>(TableId.ASSET_BALANCES, sort, tableHeaders);

const sorted = computed<AssetBalanceWithPrice[]>(() =>
  prioritizeExactMatches(sortAssetBalances([...get(matches)], get(sort), getAssetInfo)));

const expandedIndex = computed<number>(() => {
  const [row] = get(expanded);
  return row ? get(sorted).findIndex(({ asset }) => asset === row.asset) : -1;
});

const { paddingBottom, paddingTop, visibleRows, windowed } = useTableRowWindow(sorted, {
  enabled: get(fillsPanel),
  expandedIndex,
  table: useTemplateRef('table'),
});

const { modelSelected, onClickCapture } = useWindowedSelectAll(selected, {
  all: () => get(sorted).map(({ asset }) => asset),
  enabled: windowed,
  rendered: () => get(visibleRows).map(({ asset }) => asset),
});

/**
 * A panel lists every row on one page with no bar.
 *
 * @remarks
 * Its page size follows the row count, so it must stay out of the app-wide rows-per-page: a table
 * syncing its limit there would rewrite every other table's page size, and the saved setting, to
 * however many assets the panel shows. Off a panel the prop is left unset, so the default applies.
 *
 * A windowed panel hands the table only the rows in view. It selects across pages, so a selected
 * row that scrolls out of view stays selected.
 */
const panelTableProps = computed<Record<string, unknown>>(() => get(fillsPanel)
  ? {
      globalItemsPerPage: false,
      hidePagination: true,
      multiPageSelect: windowed,
      pagination: { limit: Math.max(get(visibleRows).length, 1), page: 1, total: get(visibleRows).length },
    }
  : {});
</script>

<template>
  <RuiDataTable
    ref="table"
    v-model="modelSelected"
    v-model:sort.external="sort"
    :cols="tableHeaders"
    :rows="visibleRows"
    :loading="loading"
    :expanded="expanded"
    :loading-text="t('asset_balances.loading')"
    :empty="{ description: t('data_table.no_data') }"
    :sticky-header="stickyHeader"
    v-bind="panelTableProps"
    row-attr="asset"
    single-expand
    :outlined="!fillsPanel"
    dense
    @click.capture="onClickCapture($event)"
  >
    <template
      v-if="paddingTop > 0"
      #body.prepend="{ colspan }"
    >
      <tr
        aria-hidden="true"
        data-testid="asset-balances-spacer-top"
      >
        <td
          :colspan="colspan"
          class="p-0 border-0"
          :style="{ height: `${paddingTop}px` }"
        />
      </tr>
    </template>
    <template #item.asset="{ row }">
      <AssetDetails
        :asset="row.asset"
        :resolution="{ isCollectionParent: !!row.breakdown }"
        :display="nested ? { dense: true, inline: true, size: '24px' } : undefined"
      />
    </template>
    <template #item.perProtocol="{ row }">
      <BalanceTopProtocols
        v-if="row.perProtocol"
        :protocols="row.perProtocol"
        :loading="!row.price || row.price.lt(0)"
        :asset="row.asset"
      />
    </template>
    <template #item.price="{ row }">
      <FiatDisplay
        :value="row.price"
        :loading="!row.price || row.price.lt(0)"
        :price-asset="row.asset"
      />
    </template>
    <template #item.amount="{ row }">
      <ValueDisplay :value="row.amount" />
    </template>
    <template #item.value="{ row }">
      <AssetValueDisplay
        :asset="row.asset"
        :amount="row.amount"
        :price="row.price"
        :value="row.value"
        :loading="isValuePending(row)"
      />
    </template>
    <template #item.percentageOfTotalNetValue="{ row }">
      <PercentageDisplay
        :value="percentageOfTotalNetValue(row.value)"
        :asset-padding="0.1"
      />
    </template>
    <template #item.percentageOfTotalCurrentGroup="{ row }">
      <PercentageDisplay
        :value="percentageOfCurrentGroup(row.value)"
        :asset-padding="0.1"
      />
    </template>
    <template
      v-if="debouncedSearch.length > 0"
      #no-data
    >
      <TableEmptyNotice
        icon="lu-search-x"
        :title="t('asset_balances.no_match.title')"
        :description="t('asset_balances.no_match.description', { search: debouncedSearch })"
      >
        <RuiButton
          variant="outlined"
          color="primary"
          data-testid="asset-balances-clear-search"
          @click="search = ''"
        >
          {{ t('asset_balances.no_match.clear') }}
        </RuiButton>
      </TableEmptyNotice>
    </template>
    <template
      v-else-if="$slots.empty"
      #no-data
    >
      <slot name="empty" />
    </template>
    <template
      v-if="matches.length > 0 && !nested"
      #body.append
    >
      <RowAppend
        :label-colspan="rowAppendLabelColspan"
        :label="t('common.total')"
        :is-mobile="false"
        :right-patch-colspan="2"
      >
        <FiatDisplay
          :value="total"
          :loading="totalPending"
          class="font-bold"
        />
      </RowAppend>
    </template>
    <template
      v-else-if="paddingBottom > 0"
      #body.append="{ colspan }"
    >
      <tr
        aria-hidden="true"
        data-testid="asset-balances-spacer-bottom"
      >
        <td
          :colspan="colspan"
          class="p-0 border-0"
          :style="{ height: `${paddingBottom}px` }"
        />
      </tr>
    </template>
    <template #expanded-item="{ row }">
      <AssetRowDetails
        :row="row"
        :loading="loading"
        :breakdown="breakdown"
      />
    </template>
    <template #item.expand="{ row }">
      <RuiTableRowExpander
        v-if="shouldShowRowExpander(row)"
        :expanded="isExpanded(row.asset)"
        @click="expand(row)"
      />
    </template>
  </RuiDataTable>
</template>
