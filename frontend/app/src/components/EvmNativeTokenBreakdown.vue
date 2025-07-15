<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import { type AssetBalance, type BigNumber, Blockchain } from '@rotki/common';
import Eth2ValidatorLimitTooltip from '@/components/accounts/blockchain/eth2/Eth2ValidatorLimitTooltip.vue';
import IconTokenDisplay from '@/components/accounts/IconTokenDisplay.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import { groupAssetBreakdown } from '@/utils/balances';
import { calculatePercentage } from '@/utils/calculation';

const props = withDefaults(defineProps<{
  identifier: string;
  assets: string[];
  details?: {
    groupId?: string;
    chains?: string[];
  };
  blockchainOnly?: boolean;
  showPercentage?: boolean;
  total?: BigNumber;
  isLiability?: boolean;
}>(), {
  blockchainOnly: false,
  isLiability: false,
  showPercentage: false,
  total: undefined,
});

const { t } = useI18n({ useScope: 'global' });

const { blockchainOnly, showPercentage, total } = toRefs(props);
const { useAssetBreakdown } = useAssetBalancesBreakdown();
const { matchChain } = useSupportedChains();

const breakdown = computed<Record<string, AssetBreakdown[]>>(() => {
  const assets = props.assets.length > 0 ? props.assets : [props.identifier];
  const breakdown: Record<string, AssetBreakdown[]> = {};
  const details = props.details;
  const isLiability = props.isLiability;

  for (const asset of assets) {
    breakdown[asset] = get(useAssetBreakdown(asset, isLiability, {
      ...details,
      blockchainOnly: get(blockchainOnly),
    }));
  }

  return breakdown;
});

const rows = computed<AssetBreakdown[]>(() => {
  const data: AssetBreakdown[] = Object.values(get(breakdown)).reduce((acc, item) => {
    acc.push(...item);
    return acc;
  }, []);
  return groupAssetBreakdown(data, item =>
    // TODO: Remove this when https://github.com/rotki/rotki/issues/6725 is resolved.
    matchChain(item.location) || item.location);
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const sort = ref<DataTableSortData<AssetBreakdown>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const cols = computed<DataTableColumn<AssetBreakdown>[]>(() => {
  const cols: DataTableColumn<AssetBreakdown>[] = [{
    align: 'center',
    cellClass: 'py-2',
    class: 'text-no-wrap',
    key: 'location',
    label: t('common.location'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-2',
    class: 'w-full',
    key: 'tokens',
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-2',
    class: 'w-full',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  }, {
    align: 'end',
    cellClass: 'py-2',
    key: 'usdValue',
    label: t('asset_locations.header.value', {
      symbol: get(currencySymbol) ?? CURRENCY_USD,
    }),
    sortable: true,
  }];

  if (get(showPercentage)) {
    cols.push({
      align: 'end',
      cellClass: 'py-2',
      class: 'text-no-wrap',
      key: 'percentage',
      label: t('asset_locations.header.percentage'),
    });
  }

  return cols;
});

useRememberTableSorting<AssetBreakdown>(TableId.EVM_NATIVE_TOKEN_BREAKDOWN, sort, cols);

function percentage(value: BigNumber) {
  const totalVal = get(total);
  if (!totalVal)
    return '';

  return calculatePercentage(value, totalVal);
}

function getAssets(location: string): AssetBalance[] {
  const balances: AssetBalance[] = [];
  const perAsset = get(breakdown);

  for (const asset of Object.keys(perAsset)) {
    const entries = perAsset[asset];
    const entry = entries.find(entry => entry.location === location);
    if (entry) {
      balances.push({
        amount: entry.amount,
        asset,
        usdValue: entry.usdValue,
      });
    }
  }

  return balances;
}
</script>

<template>
  <RuiDataTable
    v-model:sort="sort"
    :cols="cols"
    :rows="rows"
    :empty="{ description: t('data_table.no_data') }"
    row-attr="location"
    outlined
  >
    <template #item.location="{ row }">
      <LocationDisplay
        :identifier="row.location"
        :detail-path="row.detailPath"
      />
    </template>
    <template #item.tokens="{ row }">
      <IconTokenDisplay
        show-chain
        :assets="getAssets(row.location)"
        :loading="false"
      />
    </template>
    <template #item.amount="{ row }">
      <AmountDisplay :value="row.amount" />
    </template>
    <template #item.usdValue="{ row }">
      <div class="flex items-center justify-end gap-2">
        <Eth2ValidatorLimitTooltip v-if="row.location === Blockchain.ETH2" />

        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="identifier"
          fiat-currency="USD"
          :value="row.usdValue"
        />
      </div>
    </template>
    <template #item.percentage="{ row }">
      <PercentageDisplay
        :value="percentage(row.usdValue)"
        :asset-padding="0.1"
      />
    </template>
  </RuiDataTable>
</template>
