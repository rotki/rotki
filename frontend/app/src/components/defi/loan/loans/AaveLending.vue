<template>
  <v-row>
    <v-col cols="12">
      <loan-header v-if="loan.owner" class="mt-8 mb-6" :owner="loan.owner">
        {{ tc('aave_lending.header', 0, { asset: symbol }) }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <aave-collateral :loan="loan" />
        </v-col>

        <v-col cols="12" md="6" class="pt-8 pt-md-0 ps-md-4">
          <loan-debt :debt="loan.debt" :asset="loan.asset" />
        </v-col>
      </v-row>
      <v-row no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card v-if="!premium" :title="tc('aave_lending.history')" />
          <aave-borrowing-details
            v-else
            :loading="aaveHistoryLoading"
            :events="loan.events"
            :owner="loan.owner"
            :total-lost="loan.totalLost"
            :liquidation-earned="loan.liquidationEarned"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import AaveCollateral from '@/components/defi/loan/loans/aave/AaveCollateral.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import { isSectionLoading } from '@/composables/common';
import { getPremium } from '@/composables/session';
import { AaveBorrowingDetails } from '@/premium/premium';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section } from '@/store/const';
import { AaveLoan } from '@/store/defi/types';

export default defineComponent({
  name: 'AaveLending',
  components: {
    AaveCollateral,
    PremiumCard,
    LoanDebt,
    LoanHeader,
    AaveBorrowingDetails
  },
  props: {
    loan: {
      required: true,
      type: Object as PropType<AaveLoan>
    }
  },
  setup(props) {
    const { loan } = toRefs(props);
    const premium = getPremium();
    const aaveHistoryLoading = isSectionLoading(Section.DEFI_AAVE_HISTORY);
    const { getAssetSymbol } = useAssetInfoRetrieval();
    const { tc } = useI18n();
    const symbol = computed(() => {
      const asset = get(loan).asset;
      return asset ? getAssetSymbol(asset) : '';
    });
    return {
      premium,
      aaveHistoryLoading,
      symbol,
      tc
    };
  }
});
</script>
