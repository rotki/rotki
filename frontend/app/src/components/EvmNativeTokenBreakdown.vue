<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import { type AssetBalance, type BigNumber, Blockchain } from '@rotki/common';
import Eth2ValidatorLimitTooltip from '@/components/accounts/blockchain/eth2/Eth2ValidatorLimitTooltip.vue';
import IconTokenDisplay from '@/components/accounts/IconTokenDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { FiatDisplay, ValueDisplay } from '@/modules/amount-display/components';
import { CURRENCY_USD } from '@/modules/amount-display/currencies';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { calculatePercentage } from '@/modules/common/data/calculation';
import { groupAssetBreakdown } from '@/modules/common/display/balances';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';

const {
  assets,
  blockchainOnly = false,
  details,
  identifier,
  isLiability = false,
  showPercentage = false,
  total,
} = defineProps<{
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
}>();

const { t } = useI18n({ useScope: 'global' });

const { getAssetBreakdown } = useAssetBalancesBreakdown();
const { matchChain } = useSupportedChains();

const breakdown = computed<Record<string, AssetBreakdown[]>>(() => {
  const usedAssets = assets.length > 0 ? assets : [identifier];
  const breakdown: Record<string, AssetBreakdown[]> = {};

  for (const asset of usedAssets) {
    breakdown[asset] = getAssetBreakdown(asset, isLiability, {
      ...details,
      blockchainOnly,
    });
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
  column: 'value',
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
    key: 'value',
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol) ?? CURRENCY_USD,
    }),
    sortable: true,
  }];

  if (showPercentage) {
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
  if (!total)
    return '';

  return calculatePercentage(value, total);
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
        value: entry.value,
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
      <ValueDisplay :value="row.amount" />
    </template>
    <template #item.value="{ row }">
      <div class="flex items-center justify-end gap-2">
        <Eth2ValidatorLimitTooltip v-if="row.location === Blockchain.ETH2" />

        <FiatDisplay :value="row.value" />
      </div>
    </template>
    <template #item.percentage="{ row }">
      <PercentageDisplay
        :value="percentage(row.value)"
        :asset-padding="0.1"
      />
    </template>
  </RuiDataTable>
</template>
