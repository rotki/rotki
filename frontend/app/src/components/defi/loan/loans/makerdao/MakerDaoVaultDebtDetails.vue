<template>
  <fragment>
    <v-divider class="my-4" />
    <loan-row title="Stability fee" class="mb-2">
      <percentage-display :value="stabilityFee" :asset-padding="assetPadding" />
    </loan-row>
    <loan-row title="Total lost due to interest">
      <div v-if="premium">
        <amount-display
          v-if="totalInterestOwed && !totalInterestOwed.isNegative()"
          :asset-padding="assetPadding"
          :value="totalInterestOwed"
          asset="DAI"
        />
        <amount-display
          v-else
          :asset-padding="assetPadding"
          :loading="totalInterestOwed === undefined"
          :value="'0.00'"
          asset="DAI"
        />
      </div>
      <div v-else>
        <premium-lock />
      </div>
    </loan-row>
  </fragment>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { BigNumber } from 'bignumber.js';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import Fragment from '@/components/helper/Fragment';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { getPremium } from '@/composables/session';

export default defineComponent({
  name: 'MakerDaoVaultDebtDetails',
  components: { PremiumLock, LoanRow, Fragment },
  props: {
    totalInterestOwed: {
      type: Object as PropType<BigNumber>,
      required: true
    },
    stabilityFee: {
      type: String,
      required: true
    }
  },
  setup() {
    const premium = getPremium();
    return {
      premium,
      assetPadding: 4
    };
  }
});
</script>
