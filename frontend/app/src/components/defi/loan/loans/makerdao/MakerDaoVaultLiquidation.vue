<template>
  <stat-card :title="tc('loan_liquidation.title')" :class="$style.liquidation">
    <div class="pb-5" :class="$style.upper">
      <loan-row :title="tc('loan_liquidation.liquidation_price')">
        <amount-display fiat-currency="USD" :value="vault.liquidationPrice" />
      </loan-row>
      <v-divider class="my-4" />
      <loan-row :title="tc('loan_liquidation.minimum_ratio')" :medium="false">
        <percentage-display :value="vault.liquidationRatio" />
      </loan-row>
    </div>
    <div>
      <span :class="$style.header" :style="fontStyle">
        {{ tc('loan_liquidation.liquidation_events') }}
      </span>
      <v-skeleton-loader
        v-if="premium"
        :loading="typeof vault.totalLiquidated === 'undefined'"
        class="mx-auto pt-3"
        max-width="450"
        type="paragraph"
      >
        <div v-if="vault.totalLiquidated && vault.totalLiquidated.amount.gt(0)">
          <div class="mb-2">
            <loan-row :title="tc('loan_liquidation.liquidated_collateral')">
              <amount-display
                :asset-padding="assetPadding"
                :value="vault.totalLiquidated.amount"
                :asset="vault.collateral.asset"
              />
            </loan-row>
            <loan-row :medium="false">
              <amount-display
                :asset-padding="assetPadding"
                :value="vault.totalLiquidated.usdValue"
                fiat-currency="USD"
              />
            </loan-row>
          </div>
          <loan-row :title="tc('loan_liquidation.outstanding_debt')">
            <amount-display
              :asset-padding="assetPadding"
              :value="vault.totalInterestOwed"
              asset="DAI"
            />
          </loan-row>
          <v-divider class="my-4" />
          <loan-row :title="tc('loan_liquidation.total_value_lost')">
            <amount-display
              :asset-padding="assetPadding"
              :value="valueLost"
              fiat-currency="USD"
            />
          </loan-row>
        </div>
        <div v-else v-text="tc('loan_liquidation.no_events')" />
      </v-skeleton-loader>
      <div v-else class="text-right">
        <premium-lock />
      </div>
    </div>
  </stat-card>
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
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { useTheme } from '@/composables/common';
import { getPremium } from '@/composables/session';
import { MakerDAOVaultModel } from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

export default defineComponent({
  name: 'MakerDaoVaultLiquidation',
  components: {
    PercentageDisplay,
    LoanRow,
    AmountDisplay,
    PremiumLock,
    StatCard
  },
  props: {
    vault: {
      required: true,
      type: Object as PropType<MakerDAOVaultModel>
    }
  },
  setup(props) {
    const { vault } = toRefs(props);
    const premium = getPremium();
    const { fontStyle } = useTheme();
    const { tc } = useI18n();

    const valueLost = computed(() => {
      const makerVault = get(vault);
      if (!('totalInterestOwed' in makerVault)) {
        return Zero;
      }
      const { totalInterestOwed, totalLiquidated } = makerVault;
      return totalLiquidated.usdValue.plus(totalInterestOwed);
    });

    return {
      valueLost,
      premium,
      assetPadding: 3,
      fontStyle,
      tc
    };
  }
});
</script>

<style lang="scss" module>
.header {
  font-size: 20px;
  font-weight: 500;
}

.upper {
  min-height: 100px;
  height: 45%;
}

.liquidation {
  height: 100%;
  display: flex;
  flex-direction: column;

  ::v-deep {
    .v-card {
      &__text {
        display: flex;
        flex-direction: column;
      }
    }
  }
}
</style>
