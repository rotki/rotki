<template>
  <v-row>
    <v-col cols="12">
      <loan-header class="mt-8 mb-6" :owner="loan.owner">
        {{
          $t('liquity_lending.header', { troveId: loan.balances.trove.troveId })
        }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <liquity-collateral :collateral="collateral" :ratio="ratio" />
        </v-col>
        <v-col cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
          <liquity-liquidation
            :price="liquidationPrice"
            :asset="collateral.asset"
          />
        </v-col>
        <v-col cols="12" md="6" class="ps-md-0 pt-8 pe-md-4">
          <loan-debt :debt="debt" :asset="debt.asset" />
        </v-col>
        <v-col
          v-if="premium && loan.balances.stake"
          cols="12"
          md="6"
          class="ps-md-4 pt-8 pt-md-8"
        >
          <premium-card v-if="!premium" :title="$t('liquity_lending.stake')" />
          <liquity-stake :stake="loan.balances.stake" />
        </v-col>
      </v-row>
      <v-row no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="$t('liquity_lending.trove_events')"
          />
          <liquity-trove-events
            v-else
            :events="loan.events.trove"
            :loading="loadingEvents"
          />
        </v-col>
      </v-row>
      <v-row v-if="premium && loan.events.stake" no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="$t('liquity_lending.stake_events')"
          />
          <liquity-stake-events
            v-else
            :events="loan.events.stake"
            :loading="loadingEvents"
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
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import LiquityCollateral from '@/components/defi/loan/loans/liquity/LiquityCollateral.vue';
import LiquityLiquidation from '@/components/defi/loan/loans/liquity/LiquityLiquidation.vue';
import LiquityStake from '@/components/defi/loan/loans/liquity/LiquityStake.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import { isSectionLoading } from '@/composables/common';
import { getPremium } from '@/composables/session';
import { LiquityStakeEvents, LiquityTroveEvents } from '@/premium/premium';
import { Section } from '@/store/const';
import { LiquityLoan } from '@/store/defi/liquity/types';

export default defineComponent({
  name: 'LiquityLending',
  components: {
    LiquityStake,
    PremiumCard,
    LiquityLiquidation,
    LiquityCollateral,
    LiquityTroveEvents,
    LiquityStakeEvents,
    LoanDebt,
    LoanHeader
  },
  props: {
    loan: {
      required: true,
      type: Object as PropType<LiquityLoan>
    }
  },
  setup(props) {
    const { loan } = toRefs(props);
    const debt = computed(() => loan.value.balances.trove.debt);
    const collateral = computed(() => loan.value.balances.trove.collateral);
    const ratio = computed(
      () => loan.value.balances.trove.collateralizationRatio
    );
    const liquidationPrice = computed(
      () => loan.value.balances.trove.liquidationPrice
    );
    const premium = getPremium();
    const loadingEvents = isSectionLoading(Section.DEFI_LIQUITY_EVENTS);
    return {
      debt,
      collateral,
      ratio,
      liquidationPrice,
      premium,
      loadingEvents
    };
  }
});
</script>
