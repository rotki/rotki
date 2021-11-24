<template>
  <stat-card :title="$t('loan_liquidation.title')">
    <loan-row medium :title="$t('loan_collateral.liquidation_price')">
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
import { defineComponent, PropType } from '@vue/composition-api';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import StatCard from '@/components/display/StatCard.vue';

export default defineComponent({
  name: 'LiquityLiquidation',
  components: { LoanRow, StatCard },
  props: {
    price: {
      required: true,
      type: Object as PropType<BigNumber>
    },
    asset: {
      required: true,
      type: String
    }
  },
  setup() {
    return {
      assetPadding: 5
    };
  }
});
</script>
