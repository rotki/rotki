<template>
  <v-sheet outlined rounded>
    <data-table
      :items="assets"
      :headers="headers"
      :loading="loading"
      sort-by="balance.usdValue"
    >
      <template #item.asset="{ item }">
        <asset-details :asset="item.asset" hide-name />
      </template>
      <template #item.balance.amount="{ item }">
        <amount-display :value="item.balance.amount" />
      </template>
      <template #item.balance.usdValue="{ item }">
        <amount-display
          fiat-currency="USD"
          :value="item.balance.usdValue"
          show-currency="symbol"
        />
      </template>
      <template #item.effectiveInterestRate="{ item }">
        <percentage-display :value="item.effectiveInterestRate" />
      </template>
      <template #header.balance.usdValue>
        {{
          $t('lending_asset_table.headers.usd_value', {
            currency: currency.tickerSymbol
          })
        }}
      </template>
    </data-table>
  </v-sheet>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { DefiBalance } from '@/store/defi/types';
import { Currency } from '@/types/currency';

@Component({
  components: { DataTable, PercentageDisplay, AmountDisplay, AssetIcon },
  computed: {
    ...mapGetters('session', ['currency'])
  }
})
export default class LendingAssetTable extends Vue {
  @Prop({ required: true })
  assets!: DefiBalance[];
  @Prop({ required: false, type: Boolean })
  loading!: boolean;
  currency!: Currency;

  readonly headers: DataTableHeader[] = [
    { text: this.$tc('lending_asset_table.headers.asset'), value: 'asset' },
    {
      text: this.$tc('lending_asset_table.headers.amount'),
      value: 'balance.amount',
      align: 'end'
    },
    { text: '', value: 'balance.usdValue', align: 'end' },
    {
      text: this.$tc('lending_asset_table.headers.effective_interest_rate'),
      value: 'effectiveInterestRate',
      align: 'end'
    }
  ];
}
</script>
