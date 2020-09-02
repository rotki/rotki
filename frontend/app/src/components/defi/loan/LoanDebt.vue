<template>
  <stat-card class="loan-debt" title="Debt">
    <loan-row title="Outstanding debt">
      <amount-display :value="loan.debt.amount" :asset="loan.asset" />
    </loan-row>
    <loan-row :medium="false">
      <amount-display
        class="loan-debt__usd-value"
        :value="loan.debt.usdValue"
        fiat-currency="USD"
      />
    </loan-row>
    <v-divider v-if="isVault" class="my-4" />
    <loan-row
      v-if="isVault"
      title="Stability fee"
      class="loan-debt__stability-fee mb-2"
    >
      {{ loan.stabilityFee }}
    </loan-row>
    <loan-row v-if="isVault" title="Total interest owed">
      <div v-if="premium">
        <amount-display
          v-if="loan.totalInterestOwed && !loan.totalInterestOwed.isNegative()"
          :value="loan.totalInterestOwed"
          asset="DAI"
        />
        <amount-display
          v-else
          :loading="loan.totalInterestOwed === undefined"
          :value="'0.00'"
          asset="DAI"
        />
      </div>
      <div v-else>
        <premium-lock />
      </div>
    </loan-row>
  </stat-card>
</template>
<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import PremiumMixin from '@/mixins/premium-mixin';

@Component({
  components: { LoanRow, AmountDisplay, PremiumLock, StatCard }
})
export default class LoanDebt extends Mixins(PremiumMixin, LoanDisplayMixin) {}
</script>

<style scoped lang="scss">
.loan-debt {
  &__usd-value {
    margin-right: 14px;
  }
}
</style>
