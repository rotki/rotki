<script setup lang="ts">
import { ProtocolVersion } from '@/types/defi';
import { useYearnStore } from '@/store/defi/yearn';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
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
  { key: 'vault', label: t('yearn_asset_table.headers.vault') },
  {
    cellClass: 'w-8',
    key: 'version',
    label: t('yearn_asset_table.headers.version'),
  },
  {
    align: 'end',
    key: 'underlyingUsdValue',
    label: t('yearn_asset_table.headers.underlying_asset'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'vaultUsdValue',
    label: t('yearn_asset_table.headers.vault_asset'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'roi',
    label: t('yearn_asset_table.headers.roi'),
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
      v-model:sort="sortBy"
      :cols="columns"
      :rows="vaults"
      row-attr="vaultToken"
      outlined
      :loading="loading"
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
