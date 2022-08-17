<template>
  <v-row>
    <v-col cols="12">
      <loan-header class="mt-8 mb-6" :owner="loan.owner">
        {{ tc('liquity_lending.header', 0, { troveId: loan.balance.troveId }) }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <liquity-collateral :collateral="collateral" :ratio="ratio" />
        </v-col>
        <v-col
          v-if="liquidationPrice"
          cols="12"
          md="6"
          class="ps-md-4 pt-8 pt-md-0"
        >
          <liquity-liquidation
            :price="liquidationPrice"
            :asset="collateral.asset"
          />
        </v-col>
        <v-col
          cols="12"
          md="6"
          class=""
          :class="{
            'pt-8 ps-md-0 pe-md-4': !!liquidationPrice,
            'ps-md-4': !liquidationPrice
          }"
        >
          <loan-debt :debt="debt" :asset="debt.asset" />
        </v-col>
      </v-row>
      <v-row no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="tc('liquity_lending.trove_events')"
          />
          <liquity-trove-events
            v-else
            :events="loan.events"
            :loading="loadingEvents"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { AssetBalance } from '@rotki/common';
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
import LiquityCollateral from '@/components/defi/loan/loans/liquity/LiquityCollateral.vue';
import LiquityLiquidation from '@/components/defi/loan/loans/liquity/LiquityLiquidation.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import { isSectionLoading } from '@/composables/common';
import { getPremium } from '@/composables/session';
import { LiquityTroveEvents } from '@/premium/premium';
import { Section } from '@/store/const';
import { LiquityLoan } from '@/store/defi/liquity/types';

export default defineComponent({
  name: 'LiquityLending',
  components: {
    PremiumCard,
    LiquityLiquidation,
    LiquityCollateral,
    LiquityTroveEvents,
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
    const debt = computed<AssetBalance>(() => get(loan).balance.debt);
    const collateral = computed<AssetBalance>(
      () => get(loan).balance.collateral
    );
    const ratio = computed(() => get(loan).balance.collateralizationRatio);
    const liquidationPrice = computed(() => get(loan).balance.liquidationPrice);
    const premium = getPremium();
    const loadingEvents = isSectionLoading(Section.DEFI_LIQUITY_EVENTS);
    const { tc } = useI18n();
    return {
      debt,
      collateral,
      ratio,
      liquidationPrice,
      premium,
      loadingEvents,
      tc
    };
  }
});
</script>
