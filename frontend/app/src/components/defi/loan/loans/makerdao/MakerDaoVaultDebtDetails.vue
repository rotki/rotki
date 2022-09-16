<template>
  <fragment>
    <v-divider class="my-4" />
    <loan-row :title="tc('makerdao_vault_debt.stability_fee')" class="mb-2">
      <percentage-display :value="stabilityFee" :asset-padding="assetPadding" />
    </loan-row>
    <loan-row :title="tc('makerdao_vault_debt.total_lost')">
      <div v-if="premium">
        <amount-display
          :asset-padding="assetPadding"
          :value="interest"
          :loading="loading"
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
import { BigNumber } from '@rotki/common';
import { get } from '@vueuse/core';
import { computed, defineComponent, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import Fragment from '@/components/helper/Fragment';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { usePremium } from '@/composables/premium';
import { Zero } from '@/utils/bignumbers';

export default defineComponent({
  name: 'MakerDaoVaultDebtDetails',
  components: { PremiumLock, LoanRow, Fragment },
  props: {
    totalInterestOwed: {
      type: BigNumber,
      required: true
    },
    stabilityFee: {
      type: String,
      required: true
    },
    loading: {
      type: Boolean,
      required: true
    }
  },
  setup(props) {
    const premium = usePremium();
    const { totalInterestOwed } = toRefs(props);
    const { tc } = useI18n();
    const interest = computed(() => {
      if (get(totalInterestOwed).isNegative()) {
        return Zero;
      }
      return get(totalInterestOwed);
    });
    return {
      interest,
      premium,
      assetPadding: 4,
      tc
    };
  }
});
</script>
