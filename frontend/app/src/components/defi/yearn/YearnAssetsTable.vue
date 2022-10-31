<template>
  <card v-if="vaults.length !== 0" outlined-body>
    <template #title>
      {{ t('yearn_asset_table.title') }}
    </template>
    <data-table
      :headers="headers"
      :items="vaults"
      sort-by="roi"
      :loading="loading"
    >
      <template #item.version="{ item }">
        {{ item.version }}
      </template>
      <template #item.underlyingValue.usdValue="{ item }">
        <balance-display
          :asset="item.underlyingToken"
          :value="item.underlyingValue"
        />
      </template>
      <template #item.vaultValue.usdValue="{ item }">
        <balance-display :asset="item.vaultToken" :value="item.vaultValue" />
      </template>
      <template #item.roi="{ item }">
        <percentage-display :value="item.roi" />
      </template>
    </data-table>
  </card>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { ProtocolVersion } from '@/services/defi/consts';
import { useYearnStore } from '@/store/defi/yearn';
import { YearnVaultAsset } from '@/types/defi/yearn';

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

const { t, tc } = useI18n();

const headers: DataTableHeader[] = [
  { text: tc('yearn_asset_table.headers.vault'), value: 'vault' },
  {
    text: t('yearn_asset_table.headers.version').toString(),
    value: 'version'
  },
  {
    text: tc('yearn_asset_table.headers.underlying_asset'),
    value: 'underlyingValue.usdValue',
    align: 'end'
  },
  {
    text: tc('yearn_asset_table.headers.vault_asset'),
    value: 'vaultValue.usdValue',
    align: 'end'
  },
  {
    text: tc('yearn_asset_table.headers.roi'),
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
