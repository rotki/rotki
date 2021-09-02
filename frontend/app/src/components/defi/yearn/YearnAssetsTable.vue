<template>
  <card v-if="vaults.length !== 0" outlined-body>
    <template #title>
      {{ $t('yearn_asset_table.title') }}
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

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { ProtocolVersion } from '@/services/defi/consts';
import { YearnVaultBalance } from '@/services/defi/types/yearn';
import { DefiGetterTypes } from '@/store/defi/getters';
import { Nullable } from '@/types';

@Component({
  components: { DataTable, PercentageDisplay },
  computed: {
    ...mapGetters('defi', ['yearnVaultsAssets'])
  }
})
export default class YearnAssetsTable extends Vue {
  yearnVaultsAssets!: DefiGetterTypes.YearnVaultAssetType;

  @Prop({ required: true, type: Boolean })
  loading!: boolean;
  @Prop({ required: true, type: Array })
  selectedAddresses!: string[];
  @Prop({ required: false, default: () => null })
  version!: Nullable<ProtocolVersion>;

  get vaults(): YearnVaultBalance[] {
    let v1Assets: YearnVaultBalance[] = [];
    const addresses = this.selectedAddresses;
    if (this.version === ProtocolVersion.V1 || !this.version) {
      v1Assets = this.yearnVaultsAssets(addresses, ProtocolVersion.V1);
    }

    let v2Assets: YearnVaultBalance[] = [];
    if (this.version === ProtocolVersion.V2 || !this.version) {
      v2Assets = this.yearnVaultsAssets(addresses, ProtocolVersion.V2);
    }
    return [...v1Assets, ...v2Assets];
  }

  readonly headers: DataTableHeader[] = [
    { text: this.$tc('yearn_asset_table.headers.vault'), value: 'vault' },
    {
      text: this.$t('yearn_asset_table.headers.version').toString(),
      value: 'version'
    },
    {
      text: this.$tc('yearn_asset_table.headers.underlying_asset'),
      value: 'underlyingValue.usdValue',
      align: 'end'
    },
    {
      text: this.$tc('yearn_asset_table.headers.vault_asset'),
      value: 'vaultValue.usdValue',
      align: 'end'
    },
    {
      text: this.$tc('yearn_asset_table.headers.roi'),
      value: 'roi',
      align: 'end'
    }
  ];
}
</script>
