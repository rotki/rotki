<script setup lang="ts">
import { ProtocolVersion } from '@/types/defi';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library';
import type { YearnVaultAsset } from '@/types/defi/yearn';
import type { BigNumber } from '@rotki/common';

interface VaultAssets extends YearnVaultAsset {
  underlyingUsdValue: BigNumber;
  vaultUsdValue: BigNumber;
}

const props = withDefaults(
  defineProps<{
    loading: boolean;
    selectedAddresses: string[];
    version?: ProtocolVersion | null;
  }>(),
  {
    version: null,
  },
);
const { selectedAddresses, version } = toRefs(props);

const sortBy = ref<DataTableSortData<VaultAssets>>({
  column: 'roi',
  direction: 'desc' as const,
});

const { yearnVaultsAssets } = useYearnStore();
const { t } = useI18n();

const columns: DataTableColumn<VaultAssets>[] = [
  { label: t('yearn_asset_table.headers.vault'), key: 'vault' },
  {
    label: t('yearn_asset_table.headers.version'),
    key: 'version',
    cellClass: 'w-8',
  },
  {
    label: t('yearn_asset_table.headers.underlying_asset'),
    key: 'underlyingUsdValue',
    align: 'end',
    sortable: true,
  },
  {
    label: t('yearn_asset_table.headers.vault_asset'),
    key: 'vaultUsdValue',
    align: 'end',
    sortable: true,
  },
  {
    label: t('yearn_asset_table.headers.roi'),
    key: 'roi',
    align: 'end',
    sortable: true,
  },
];

const vaults = computed<VaultAssets[]>(() => {
  const protocolVersion = get(version);
  let v1Assets: YearnVaultAsset[] = [];

  const addresses = get(selectedAddresses);
  if (protocolVersion === ProtocolVersion.V1 || !protocolVersion)
    v1Assets = get(yearnVaultsAssets(addresses, ProtocolVersion.V1));

  let v2Assets: YearnVaultAsset[] = [];
  if (protocolVersion === ProtocolVersion.V2 || !protocolVersion)
    v2Assets = get(yearnVaultsAssets(addresses, ProtocolVersion.V2));

  return [...v1Assets, ...v2Assets].map(x => ({
    ...x,
    underlyingUsdValue: x.underlyingValue.usdValue,
    vaultUsdValue: x.vaultValue.usdValue,
  }));
});
</script>

<template>
  <RuiCard v-if="vaults.length > 0">
    <template #header>
      {{ t('yearn_asset_table.title') }}
    </template>

    <RuiDataTable
      :cols="columns"
      :rows="vaults"
      row-attr="vaultToken"
      outlined
      :sort="sortBy"
      :loading="loading"
      @update:sort="sortBy = $event"
    >
      <template #item.version="{ row }">
        {{ row.version }}
      </template>
      <template #item.underlyingUsdValue="{ row }">
        <BalanceDisplay
          :asset="row.underlyingToken"
          :value="row.underlyingValue"
        />
      </template>
      <template #item.vaultUsdValue="{ row }">
        <BalanceDisplay
          :asset="row.vaultToken"
          :value="row.vaultValue"
        />
      </template>
      <template #item.roi="{ row }">
        <PercentageDisplay :value="row.roi" />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
