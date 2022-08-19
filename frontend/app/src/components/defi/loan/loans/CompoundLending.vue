<template>
  <v-row>
    <v-col cols="12">
      <loan-header v-if="loan.owner" class="mt-8 mb-6" :owner="loan.owner">
        {{ $t('compound_lending.header', { asset: symbol }) }}
      </loan-header>
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <compound-collateral :loan="loan" />
        </v-col>
        <v-col cols="12" md="6" class="pt-8 pt-md-0 ps-md-4">
          <loan-debt :debt="loan.debt" :asset="loan.asset" />
        </v-col>
      </v-row>
      <v-row no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            :title="$t('compound_lending.history')"
          />
          <compound-borrowing-details
            v-else
            :events="loan.events"
            :owner="loan.owner"
            :assets="assets"
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
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import CompoundCollateral from '@/components/defi/loan/loans/compound/CompoundCollateral.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import { getPremium } from '@/composables/session';
import { CompoundBorrowingDetails } from '@/premium/premium';
import { CompoundLoan } from '@/services/defi/types/compound';
import { useAssetInfoRetrieval } from '@/store/assets';
import { uniqueStrings } from '@/utils/data';

export default defineComponent({
  name: 'CompoundLending',
  components: {
    LoanDebt,
    CompoundCollateral,
    PremiumCard,
    LoanHeader,
    CompoundBorrowingDetails
  },
  props: {
    loan: {
      required: true,
      type: Object as PropType<CompoundLoan>
    }
  },
  setup(props) {
    const premium = getPremium();

    const { loan } = toRefs(props);
    const assets = computed(() => {
      const { asset, events } = get(loan);
      const assets = events
        .map(({ toAsset }) => toAsset ?? '')
        .filter(uniqueStrings);

      if (asset) {
        assets.push(asset);
      }

      return assets;
    });

    const { getAssetSymbol } = useAssetInfoRetrieval();
    const symbol = computed(() => {
      const asset = get(loan).asset;
      return asset ? getAssetSymbol(asset) : '';
    });

    return {
      premium,
      assets,
      symbol
    };
  }
});
</script>
