<template>
  <stat-card :title="tc('loan_debt.title')" :class="$style.debt">
    <loan-row :title="tc('loan_debt.outstanding_debt')">
      <amount-display
        :asset-padding="assetPadding"
        :value="debt.amount"
        :asset="asset"
      />
    </loan-row>
    <loan-row :medium="false">
      <amount-display
        :asset-padding="assetPadding"
        :value="debt.usdValue"
        fiat-currency="USD"
      />
    </loan-row>
    <slot />
  </stat-card>
</template>
<script setup lang="ts">
import { Balance } from '@rotki/common';
import { PropType } from 'vue';

import LoanRow from '@/components/defi/loan/LoanRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';

defineProps({
  debt: {
    required: true,
    type: Object as PropType<Balance>
  },
  asset: {
    required: false,
    type: String,
    default: ''
  }
});

const { tc } = useI18n();
const assetPadding = 4;
</script>

<style module lang="scss">
.debt {
  height: 100%;
}
</style>
