<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { AssetBalancesDisplay, AssetBreakdownOptions } from '@/modules/balances/types/balances';
import { RuiButton, RuiDataTable, RuiTableRowExpander } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { isEvmNativeToken } from '@/modules/assets/types';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import { useAssetBalancesTable } from '@/modules/balances/use-asset-balances-table';
import { useValuePending } from '@/modules/balances/value-pending';
import { hasAwaitingClaim } from '@/modules/core/common/display/balances';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import { useTableRowWindow, useWindowedSelectAll } from '@/modules/core/table/use-table-row-window';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';

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
  display,
} = defineProps<{
  balances: AssetBalanceWithPrice[];
  breakdown?: AssetBreakdownOptions;
  loading?: boolean;
  display?: AssetBalancesDisplay;
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

const {
  debouncedSearch,
  matches,
  modelSort,
  percentageOfCurrentGroup,
  percentageOfTotalNetValue,
  sorted,
  tableHeaders,
  total,
} = useAssetBalancesTable({
  balances: () => balances,
  display: () => display,
  fillsPanel,
  search,
});
const { isTotalPending, isValuePending } = useValuePending();

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

const totalPending = computed<boolean>(() => isTotalPending(get(matches)));

const rowAppendLabelColspan = computed(() => {
  let colspan = 3;

  if (selectionMode)
    colspan++;
  if (display?.showPerProtocol)
    colspan++;

  return colspan;
});

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
    v-model:sort.external="modelSort"
    :cols="tableHeaders"
    :rows="visibleRows"
    :loading="loading"
    :expanded="expanded"
    :empty="{ description: t('data_table.no_data') }"
    :sticky-header="display?.stickyHeader ?? false"
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
      <ValueDisplay
        :value="row.amount"
        :format="display?.amountFormat?.(row.asset)"
      />
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
