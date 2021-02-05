<template>
  <v-sheet outlined rounded>
    <v-data-table
      :items="assets"
      :headers="headers"
      :loading="loading"
      :footer-props="footerProps"
      sort-desc
      sort-by="balance.usdValue"
    >
      <template #item.asset="{ item }">
        <span class="d-flex flex-row align-center">
          <crypto-icon size="26px" :symbol="item.asset" class="mr-2" />
          {{ item.asset }}
        </span>
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
            currency: currency.ticker_symbol
          })
        }}
      </template>
    </v-data-table>
  </v-sheet>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import { footerProps } from '@/config/datatable.common';
import { Currency } from '@/model/currency';
import { DefiBalance } from '@/store/defi/types';

@Component({
  components: { PercentageDisplay, AmountDisplay, CryptoIcon },
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

  readonly footerProps = footerProps;

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
