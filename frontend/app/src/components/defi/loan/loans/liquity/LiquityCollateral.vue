<template>
  <stat-card :title="tc('loan_collateral.title')">
    <loan-row medium :title="tc('loan_collateral.locked_collateral')">
      <balance-display :asset="collateral.asset" :value="collateral" />
    </loan-row>

    <v-divider v-if="ratio" class="my-4" />

    <loan-row v-if="ratio" :title="tc('loan_collateral.ratio')">
      <percentage-display :value="ratio.toFormat(2)" />
    </loan-row>
  </stat-card>
</template>

<script lang="ts">
import { AssetBalance, BigNumber } from '@rotki/common';
import { defineComponent, PropType } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
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
      type: BigNumber,
      default: null
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
