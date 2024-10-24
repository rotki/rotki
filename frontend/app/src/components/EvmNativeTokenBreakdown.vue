<script setup lang="ts">
import { type BigNumber, Blockchain } from '@rotki/common';
import { CURRENCY_USD } from '@/types/currencies';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AssetBalance } from '@/types/balances';

const props = withDefaults(
  defineProps<{
    identifier: string;
    assets: string[];
    details?: {
      groupId: string;
      chains: string[];
    };
    blockchainOnly?: boolean;
    showPercentage?: boolean;
    total?: BigNumber;
    isLiability?: boolean;
  }>(),
  {
    blockchainOnly: false,
    showPercentage: false,
    total: undefined,
    isLiability: false,
  },
);

const { t } = useI18n();

const { blockchainOnly, showPercentage, total } = toRefs(props);
const { assetBreakdown: blockchainAssetBreakdown, liabilityBreakdown: blockchainLiabilityBreakdown } = useBlockchainStore();
const { assetBreakdown, liabilityBreakdown } = useBalancesBreakdown();
const { getChain } = useSupportedChains();

const breakdown = computed<Record<string, AssetBreakdown[]>>(() => {
  const assets = props.assets.length > 0 ? props.assets : [props.identifier];
  const breakdown: Record<string, AssetBreakdown[]> = {};
  const details = props.details;
  const isLiability = props.isLiability;

  for (const asset of assets) {
    if (details || get(blockchainOnly)) {
      const func = !isLiability ? blockchainAssetBreakdown : blockchainLiabilityBreakdown;
      breakdown[asset] = get(func(asset, details?.chains, details?.groupId));
    }
    else {
      const func = !isLiability ? assetBreakdown : liabilityBreakdown;
      breakdown[asset] = get(func(asset));
    }
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
    getChain(item.location, null) || item.location);
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const sort = ref<DataTableSortData<AssetBreakdown>>({
  column: 'value',
  direction: 'desc' as const,
});

const cols = computed<DataTableColumn<AssetBreakdown>[]>(() => {
  const headers: DataTableColumn<AssetBreakdown>[] = [
    {
      label: t('common.location'),
      key: 'location',
      align: 'center',
      class: 'text-no-wrap',
      cellClass: 'py-2',
      sortable: true,
    },
    {
      key: 'tokens',
      align: 'end',
      class: 'w-full',
      cellClass: 'py-2',
      sortable: true,
    },
    {
      label: t('common.amount'),
      key: 'amount',
      align: 'end',
      class: 'w-full',
      cellClass: 'py-2',
      sortable: true,
    },
    {
      label: t('asset_locations.header.value', {
        symbol: get(currencySymbol) ?? CURRENCY_USD,
      }),
      key: 'usdValue',
      align: 'end',
      cellClass: 'py-2',
      sortable: true,
    },
  ];

  if (get(showPercentage)) {
    headers.push({
      label: t('asset_locations.header.percentage'),
      key: 'percentage',
      align: 'end',
      class: 'text-no-wrap',
      cellClass: 'py-2',
    });
  }

  return headers;
});

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
        asset,
        amount: entry.amount,
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
      <AmountDisplay :value="row.amount" />
    </template>
    <template #item.usdValue="{ row }">
      <div class="flex items-center justify-end gap-2">
        <Eth2ValidatorLimitTooltip v-if="row.location === Blockchain.ETH2" />

        <AmountDisplay
          show-currency="symbol"
          :amount="row.amount"
          :price-asset="identifier"
          :fiat-currency="currencySymbol"
          :value="row.value"
        />
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
