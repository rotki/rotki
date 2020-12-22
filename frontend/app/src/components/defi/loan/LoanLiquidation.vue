<template>
  <stat-card :title="$t('loan_liquidation.title')" class="liquidation">
    <div class="liquidation__upper pb-5">
      <loan-row :title="$t('loan_liquidation.liquidation_price')">
        <amount-display fiat-currency="USD" :value="loan.liquidationPrice" />
      </loan-row>
      <v-divider class="my-4" />
      <loan-row :title="$t('loan_liquidation.minimum_ratio')" :medium="false">
        <percentage-display :value="loan.liquidationRatio" />
      </loan-row>
    </div>
    <div>
      <span
        class="liquidation__liquidation-events__header"
        v-text="$t('loan_liquidation.liquidation_events')"
      />
      <v-skeleton-loader
        v-if="premium"
        :loading="typeof loan.totalLiquidated === 'undefined'"
        class="mx-auto pt-3"
        max-width="450"
        type="paragraph"
      >
        <div
          v-if="loan.totalLiquidated && loan.totalLiquidated.amount.gt(0)"
          class="liquidation-events__content"
        >
          <div class="liquidation-events__content__liquidated-collateral mb-2">
            <loan-row :title="$t('loan_liquidation.liquidated_collateral')">
              <amount-display
                :asset-padding="assetPadding"
                :value="loan.totalLiquidated.amount"
                :asset="loan.collateral.asset"
              />
            </loan-row>
            <loan-row :medium="false">
              <amount-display
                :asset-padding="assetPadding"
                :value="loan.totalLiquidated.usdValue"
                fiat-currency="USD"
              />
            </loan-row>
          </div>
          <loan-row :title="$t('loan_liquidation.outstanding_debt')">
            <amount-display
              :asset-padding="assetPadding"
              :value="loan.totalInterestOwed"
              asset="DAI"
            />
          </loan-row>
          <v-divider class="my-4" />
          <loan-row :title="$t('loan_liquidation.total_value_lost')">
            <amount-display
              :asset-padding="assetPadding"
              :value="
                loan.totalLiquidated.usdValue.plus(loan.totalInterestOwed)
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
import { Component, Mixins } from 'vue-property-decorator';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import PremiumMixin from '@/mixins/premium-mixin';

@Component({
  components: {
    PercentageDisplay,
    LoanRow,
    AmountDisplay,
    PremiumLock,
    StatCard
  }
})
export default class LoanLiquidation extends Mixins(
  PremiumMixin,
  LoanDisplayMixin
) {
  readonly assetPadding: number = 3;
}
</script>

<style lang="scss" scoped>
.liquidation {
  height: 100%;
  display: flex;
  flex-direction: column;

  &__upper {
    min-height: 100px;
    height: 45%;
  }

  ::v-deep {
    .v-card {
      &__text {
        display: flex;
        flex-direction: column;
      }
    }
  }

  &__liquidation-events {
    &__header {
      font-size: 20px;
      font-weight: 500;
      color: rgba(0, 0, 0, 0.87);
    }
  }
}
</style>
