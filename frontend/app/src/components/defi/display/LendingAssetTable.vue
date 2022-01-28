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
import { defineComponent, PropType } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { setupGeneralSettings } from '@/composables/session';
import i18n from '@/i18n';
import { DefiBalance } from '@/store/defi/types';

const headers: DataTableHeader[] = [
  {
    text: i18n.t('lending_asset_table.headers.asset').toString(),
    value: 'asset'
  },
  {
    text: i18n.t('lending_asset_table.headers.amount').toString(),
    value: 'balance.amount',
    align: 'end'
  },
  { text: '', value: 'balance.usdValue', align: 'end' },
  {
    text: i18n
      .t('lending_asset_table.headers.effective_interest_rate')
      .toString(),
    value: 'effectiveInterestRate',
    align: 'end'
  }
];
export default defineComponent({
  name: 'LendingAssetTable',
  components: { DataTable, PercentageDisplay, AmountDisplay },
  props: {
    assets: { required: true, type: Array as PropType<DefiBalance[]> },
    loading: { reuirqed: false, type: Boolean, default: false }
  },
  setup() {
    const { currency } = setupGeneralSettings();

    return {
      headers,
      currency
    };
  }
});
</script>
