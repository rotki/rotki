<script setup lang="ts">
import type { AssetBalance, AssetBalanceWithPrice, BigNumber, Nullable } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import { some } from 'es-toolkit/compat';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { useAssetSelectInfo } from '@/composables/assets/asset-select-info';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import AssetRowDetails from '@/modules/balances/protocols/components/AssetRowDetails.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { isEvmNativeToken } from '@/types/asset';
import { TableColumn } from '@/types/table-column';
import { assetFilterByKeyword } from '@/utils/assets';
import { sortAssetBalances } from '@/utils/balances';
import { bigNumberSum, calculatePercentage } from '@/utils/calculation';

defineOptions({
  name: 'AssetBalances',
});

const search = defineModel<string>('search', { default: '', required: false });
const selected = defineModel<string[] | undefined>('selected', { required: false });

const props = withDefaults(defineProps<{
  balances: AssetBalanceWithPrice[];
  details?: {
    groupId?: string;
    chains?: string[];
  };
  loading?: boolean;
  hideTotal?: boolean;
  hideBreakdown?: boolean;
  stickyHeader?: boolean;
  isLiability?: boolean;
  allBreakdown?: boolean;
  visibleColumns?: TableColumn[];
  showPerProtocol?: boolean;
  selectionMode?: boolean;
}>(), {
  allBreakdown: false,
  details: undefined,
  hideBreakdown: false,
  hideTotal: false,
  isLiability: false,
  loading: false,
  selectionMode: false,
  showPerProtocol: false,
  stickyHeader: false,
  visibleColumns: () => [],
});

const { t } = useI18n({ useScope: 'global' });

const { balances } = toRefs(props);
const expanded = ref<AssetBalanceWithPrice[]>([]);

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'value',
  direction: 'desc' as const,
});

const debouncedSearch = debouncedRef(search, 200);

const { assetInfo, assetName, assetSymbol } = useAssetSelectInfo();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const statistics = useStatisticsStore();
const { totalNetWorth } = storeToRefs(statistics);

const isExpanded = (asset: string) => some(get(expanded), { asset });

function shouldShowRowExpander(row: AssetBalanceWithPrice): boolean {
  const hasBreakdown = Boolean(row.breakdown);
  const shouldShowNativeBreakdown = (!props.hideBreakdown && isEvmNativeToken(row.asset)) ?? false;
  const hasPerProtocolDetails = (row.perProtocol && row.perProtocol.length > 1) ?? false;
  return hasBreakdown || shouldShowNativeBreakdown || hasPerProtocolDetails;
}

function expand(item: AssetBalanceWithPrice) {
  set(expanded, isExpanded(item.asset) ? [] : [item]);
}

function assetFilter(item: Nullable<AssetBalance>) {
  return assetFilterByKeyword(item, get(debouncedSearch), assetName, assetSymbol);
}

const filteredBalances = computed(() => get(balances).filter(assetFilter));

const total = computed<BigNumber>(() => bigNumberSum(get(filteredBalances).map(({ value }) => value)));

function percentageOfTotalNetValue(val: BigNumber): string {
  return calculatePercentage(val, get(totalNetWorth));
}

function percentageOfCurrentGroup(val: BigNumber): string {
  return calculatePercentage(val, get(total));
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
    cellClass: 'py-0',
    key: 'usdPrice',
    label: t('common.price_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-0',
    class: 'text-no-wrap',
    key: 'value',
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    sortable: true,
  }];

  if (props.showPerProtocol) {
    headers.splice(1, 0, {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'perProtocol',
      label: t('common.location'),
      sortable: false,
    });
  }

  if (props.visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalNetValue',
      label: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
    });
  }

  if (props.visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
    headers.push({
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'percentageOfTotalCurrentGroup',
      label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group: t('blockchain_balances.group_label'),
      }),
    });
  }

  return headers;
});

const rowAppendLabelColspan = computed(() => {
  let colspan = 3;

  if (props.selectionMode)
    colspan++;
  if (props.showPerProtocol)
    colspan++;

  return colspan;
});

useRememberTableSorting<AssetBalanceWithPrice>(TableId.ASSET_BALANCES, sort, tableHeaders);

const sorted = computed<AssetBalanceWithPrice[]>(() => sortAssetBalances([...get(filteredBalances)], get(sort), assetInfo));
</script>

<template>
  <RuiDataTable
    v-model="selected"
    v-model:sort.external="sort"
    :cols="tableHeaders"
    :rows="sorted"
    :loading="loading"
    :expanded="expanded"
    :loading-text="t('asset_balances.loading')"
    :empty="{ description: t('data_table.no_data') }"
    :sticky-header="stickyHeader"
    row-attr="asset"
    single-expand
    outlined
    dense
  >
    <template #item.asset="{ row }">
      <AssetDetails
        :asset="row.asset"
        :is-collection-parent="!!row.breakdown"
      />
    </template>
    <template #item.perProtocol="{ row }">
      <BalanceTopProtocols
        v-if="row.perProtocol"
        :protocols="row.perProtocol"
        :loading="!row.usdPrice || row.usdPrice.lt(0)"
        :asset="row.asset"
      />
    </template>
    <template #item.usdPrice="{ row }">
      <AmountDisplay
        :loading="!row.usdPrice || row.usdPrice.lt(0)"
        is-asset-price
        show-currency="symbol"
        :price-asset="row.asset"
        :price-of-asset="row.usdPrice"
        fiat-currency="USD"
        :value="row.usdPrice"
      />
    </template>
    <template #item.amount="{ row }">
      <AmountDisplay :value="row.amount" />
    </template>
    <template #item.value="{ row }">
      <AmountDisplay
        show-currency="symbol"
        :amount="row.amount"
        :price-asset="row.asset"
        :price-of-asset="row.usdPrice"
        force-currency
        :value="row.value"
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
      v-if="balances.length > 0 && !hideTotal"
      #body.append
    >
      <RowAppend
        :label-colspan="rowAppendLabelColspan"
        :label="t('common.total')"
        :is-mobile="false"
        :right-patch-colspan="2"
        class-name="[&>td]:p-4 text-sm"
      >
        <AmountDisplay
          force-currency
          show-currency="symbol"
          :value="total"
        />
      </RowAppend>
    </template>
    <template #expanded-item="{ row }">
      <AssetRowDetails
        :row="row"
        :details="details"
        :loading="loading"
        :is-liability="isLiability"
        :all-breakdown="allBreakdown"
        :hide-breakdown="hideBreakdown"
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
