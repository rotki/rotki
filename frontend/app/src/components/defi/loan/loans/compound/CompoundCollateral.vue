<template>
  <stat-card :title="tc('loan_collateral.title')">
    <loan-row medium :title="tc('loan_collateral.locked_collateral')">
      <amount-display
        :asset-padding="assetPadding"
        :value="totalCollateralUsd"
        fiat-currency="USD"
      />
    </loan-row>
    <v-divider class="my-4" />
    <loan-row
      v-if="loan.collateral.length > 0"
      :title="tc('loan_collateral.per_asset')"
    >
      <v-row
        v-for="collateral in loan.collateral"
        :key="collateral.asset"
        no-gutters
      >
        <v-col>
          <balance-display :asset="collateral.asset" :value="collateral" />
        </v-col>
      </v-row>
    </loan-row>
    <v-divider v-if="loan.collateral.length > 0" class="my-4" />

    <loan-row :title="tc('loan_collateral.apy')">
      <percentage-display :value="loan.apy ? loan.apy : null" />
    </loan-row>
  </stat-card>
</template>

<script lang="ts">
import { defineComponent, PropType, toRefs } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import { totalCollateral } from '@/components/defi/loan/loans/total-collateral';
import StatCard from '@/components/display/StatCard.vue';
import { CompoundLoan } from '@/services/defi/types/compound';

export default defineComponent({
  name: 'CompoundCollateral',
  components: { LoanRow, StatCard },
  props: {
    loan: {
      required: true,
      type: Object as PropType<CompoundLoan>
    }
  },
  setup(props) {
    const { loan } = toRefs(props);
    const { tc } = useI18n();

    return {
      totalCollateralUsd: totalCollateral(loan),
      assetPadding: 5,
      tc
    };
  }
});
</script>
