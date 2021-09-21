<template>
  <stat-card :title="$t('loan_liquidation.title')" :class="$style.liquidation">
    <div class="pb-5" :class="$style.upper">
      <loan-row :title="$t('loan_liquidation.liquidation_price')">
        <amount-display fiat-currency="USD" :value="vault.liquidationPrice" />
      </loan-row>
      <v-divider class="my-4" />
      <loan-row :title="$t('loan_liquidation.minimum_ratio')" :medium="false">
        <percentage-display :value="vault.liquidationRatio" />
      </loan-row>
    </div>
    <div>
      <span :class="$style.header" :style="fontStyle">
        {{ $t('loan_liquidation.liquidation_events') }}
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
            <loan-row :title="$t('loan_liquidation.liquidated_collateral')">
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
          <loan-row :title="$t('loan_liquidation.outstanding_debt')">
            <amount-display
              :asset-padding="assetPadding"
              :value="vault.totalInterestOwed"
              asset="DAI"
            />
          </loan-row>
          <v-divider class="my-4" />
          <loan-row :title="$t('loan_liquidation.total_value_lost')">
            <amount-display
              :asset-padding="assetPadding"
              :value="
                vault.totalLiquidated.usdValue.plus(vault.totalInterestOwed)
              "
              fiat-currency="USD"
            />
          </loan-row>
        </div>
        <div v-else v-text="$t('loan_liquidation.no_events')" />
      </v-skeleton-loader>
      <div v-else class="text-right">
        <premium-lock />
      </div>
    </div>
  </stat-card>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { getPremium } from '@/composables/session';
import ThemeMixin from '@/mixins/theme-mixin';
import { MakerDAOVaultModel } from '@/store/defi/types';

export default defineComponent({
  name: 'MakerDaoVaultLiquidation',
  components: {
    PercentageDisplay,
    LoanRow,
    AmountDisplay,
    PremiumLock,
    StatCard
  },
  mixins: [ThemeMixin],
  props: {
    vault: {
      required: true,
      type: Object as PropType<MakerDAOVaultModel>
    }
  },
  setup() {
    const premium = getPremium();
    return {
      premium,
      assetPadding: 3
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
