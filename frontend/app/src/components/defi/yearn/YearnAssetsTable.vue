<template>
  <v-card>
    <v-card-title>
      <card-title> {{ $t('yearn_asset_table.title') }} </card-title>
    </v-card-title>
    <v-card-text>
      <v-sheet outlined rounded>
        <data-table
          :headers="headers"
          :items="yearnVaultsAssets(selectedAddresses)"
          sort-by="roi"
          :loading="loading"
        >
          <template #item.underlyingValue.usdValue="{ item }">
            <balance-display
              :asset="item.underlyingToken"
              :value="item.underlyingValue"
            />
          </template>
          <template #item.vaultValue.usdValue="{ item }">
            <balance-display
              :asset="item.vaultToken"
              :value="item.vaultValue"
            />
          </template>
          <template #item.roi="{ item }">
            <percentage-display :value="item.roi" />
          </template>
        </data-table>
      </v-sheet>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { YearnVaultBalance } from '@/services/defi/types/yearn';

@Component({
  components: { DataTable, PercentageDisplay },
  computed: {
    ...mapGetters('defi', ['yearnVaultsAssets'])
  }
})
export default class YearnAssetsTable extends Vue {
  yearVaultsAssets!: (selectedAddresses: string[]) => YearnVaultBalance[];

  @Prop({ required: true, type: Boolean })
  loading!: boolean;
  @Prop({ required: true, type: Array })
  selectedAddresses!: string[];

  readonly headers: DataTableHeader[] = [
    { text: this.$tc('yearn_asset_table.headers.vault'), value: 'vault' },
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
