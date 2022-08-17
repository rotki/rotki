<template>
  <stat-card :title="tc('loan_liquidation.title')">
    <loan-row medium :title="tc('loan_collateral.liquidation_price')">
      <amount-display
        show-currency="ticker"
        fiat-currency="USD"
        :value="price"
        :min-width="18"
      />
    </loan-row>
  </stat-card>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { defineComponent } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import StatCard from '@/components/display/StatCard.vue';

export default defineComponent({
  name: 'LiquityLiquidation',
  components: { LoanRow, StatCard },
  props: {
    price: {
      required: true,
      type: BigNumber
    },
    asset: {
      required: true,
      type: String
    }
  },
  setup() {
    const { tc } = useI18n();
    return {
      assetPadding: 5,
      tc
    };
  }
});
</script>
