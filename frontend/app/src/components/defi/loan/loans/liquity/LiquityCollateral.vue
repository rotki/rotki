<template>
  <stat-card :title="$t('loan_collateral.title')">
    <loan-row medium :title="$t('loan_collateral.locked_collateral')">
      <balance-display
        :asset="collateral.asset"
        :value="collateral"
        :min-width="18"
      />
    </loan-row>

    <v-divider v-if="ratio" class="my-4" />

    <loan-row v-if="ratio" :title="$t('loan_collateral.ratio')">
      <percentage-display :value="ratio.toFormat(2)" />
    </loan-row>
  </stat-card>
</template>

<script lang="ts">
import { AssetBalance, BigNumber } from '@rotki/common';
import { defineComponent, PropType } from '@vue/composition-api';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import StatCard from '@/components/display/StatCard.vue';

export default defineComponent({
  name: 'LiquityCollateral',
  components: { LoanRow, StatCard },
  props: {
    collateral: {
      required: true,
      type: Object as PropType<AssetBalance>
    },
    ratio: {
      required: false,
      type: Object as PropType<BigNumber>,
      default: null
    }
  },
  setup() {
    return {
      assetPadding: 5
    };
  }
});
</script>
