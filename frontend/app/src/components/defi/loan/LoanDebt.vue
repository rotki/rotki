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
<script lang="ts">
import { Balance } from '@rotki/common';
import { defineComponent, PropType } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';

export default defineComponent({
  name: 'LoanDebt',
  components: {
    LoanRow,
    AmountDisplay,
    StatCard
  },
  props: {
    debt: {
      required: true,
      type: Object as PropType<Balance>
    },
    asset: {
      required: true,
      type: String
    }
  },
  setup() {
    const { tc } = useI18n();
    return {
      tc,
      assetPadding: 4
    };
  }
});
</script>

<style module lang="scss">
.debt {
  height: 100%;
}
</style>
