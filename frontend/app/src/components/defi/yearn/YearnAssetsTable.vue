<script setup lang="ts">
import { type PropType } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type YearnVaultAsset } from '@/types/defi/yearn';
import { ProtocolVersion } from '@/types/defi';

const props = defineProps({
  loading: { required: true, type: Boolean },
  selectedAddresses: { required: true, type: Array as PropType<string[]> },
  version: {
    required: false,
    default: () => null,
    type: String as PropType<ProtocolVersion | null>
  }
});
const { selectedAddresses, version } = toRefs(props);
const { yearnVaultsAssets } = useYearnStore();

const { t } = useI18n();

const headers: DataTableHeader[] = [
  { text: t('yearn_asset_table.headers.vault'), value: 'vault' },
  {
    text: t('yearn_asset_table.headers.version').toString(),
    value: 'version'
  },
  {
    text: t('yearn_asset_table.headers.underlying_asset'),
    value: 'underlyingValue.usdValue',
    align: 'end'
  },
  {
    text: t('yearn_asset_table.headers.vault_asset'),
    value: 'vaultValue.usdValue',
    align: 'end'
  },
  {
    text: t('yearn_asset_table.headers.roi'),
    value: 'roi',
    align: 'end'
  }
];

const vaults = computed(() => {
  const protocolVersion = get(version);
  let v1Assets: YearnVaultAsset[] = [];

  const addresses = get(selectedAddresses);
  if (protocolVersion === ProtocolVersion.V1 || !protocolVersion) {
    v1Assets = get(yearnVaultsAssets(addresses, ProtocolVersion.V1));
  }

  let v2Assets: YearnVaultAsset[] = [];
  if (protocolVersion === ProtocolVersion.V2 || !protocolVersion) {
    v2Assets = get(yearnVaultsAssets(addresses, ProtocolVersion.V2));
  }
  return [...v1Assets, ...v2Assets];
});
</script>

<template>
  <Card v-if="vaults.length > 0">
    <template #title>
      {{ t('yearn_asset_table.title') }}
    </template>
    <DataTable
      :headers="headers"
      :items="vaults"
      sort-by="roi"
      :loading="loading"
    >
      <template #item.version="{ item }">
        {{ item.version }}
      </template>
      <template #item.underlyingValue.usdValue="{ item }">
        <BalanceDisplay
          :asset="item.underlyingToken"
          :value="item.underlyingValue"
        />
      </template>
      <template #item.vaultValue.usdValue="{ item }">
        <BalanceDisplay :asset="item.vaultToken" :value="item.vaultValue" />
      </template>
      <template #item.roi="{ item }">
        <PercentageDisplay :value="item.roi" />
      </template>
    </DataTable>
  </Card>
</template>
