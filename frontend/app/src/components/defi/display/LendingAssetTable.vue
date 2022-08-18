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
            currency: currencySymbol
          })
        }}
      </template>
    </data-table>
  </v-sheet>
</template>

<script lang="ts">
import { computed, defineComponent, PropType } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { BaseDefiBalance } from '@/store/defi/types';
import { useGeneralSettingsStore } from '@/store/settings/general';

export default defineComponent({
  name: 'LendingAssetTable',
  components: { DataTable, PercentageDisplay, AmountDisplay },
  props: {
    assets: { required: true, type: Array as PropType<BaseDefiBalance[]> },
    loading: { required: false, type: Boolean, default: false }
  },
  setup() {
    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const { tc } = useI18n();

    const headers = computed<DataTableHeader[]>(() => [
      {
        text: tc('common.asset'),
        value: 'asset'
      },
      {
        text: tc('common.amount'),
        value: 'balance.amount',
        align: 'end'
      },
      { text: '', value: 'balance.usdValue', align: 'end' },
      {
        text: tc('lending_asset_table.headers.effective_interest_rate'),
        value: 'effectiveInterestRate',
        align: 'end'
      }
    ]);

    return {
      headers,
      currencySymbol
    };
  }
});
</script>
