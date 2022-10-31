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
        :loading="!liquidated"
        class="mx-auto pt-3"
        max-width="450"
        type="paragraph"
      >
        <div v-if="liquidated && liquidated.amount.gt(0)">
          <div class="mb-2">
            <loan-row :title="tc('loan_liquidation.liquidated_collateral')">
              <amount-display
                :asset-padding="assetPadding"
                :value="liquidated.amount"
                :asset="vault.collateral.asset"
              />
            </loan-row>
            <loan-row :medium="false">
              <amount-display
                :asset-padding="assetPadding"
                :value="liquidated.usdValue"
                fiat-currency="USD"
              />
            </loan-row>
          </div>
          <loan-row :title="tc('loan_liquidation.outstanding_debt')">
            <amount-display
              :asset-padding="assetPadding"
              :value="totalInterestOwed"
              :asset="dai"
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
<script setup lang="ts">
import { assetSymbolToIdentifierMap } from '@rotki/common/lib/data';
import { PropType } from 'vue';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { useTheme } from '@/composables/common';
import { usePremium } from '@/composables/premium';
import { MakerDAOVaultModel } from '@/types/defi/maker';
import { Zero } from '@/utils/bignumbers';

const assetPadding = 3;

const props = defineProps({
  vault: {
    required: true,
    type: Object as PropType<MakerDAOVaultModel>
  }
});

const { vault } = toRefs(props);
const premium = usePremium();
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

const liquidated = computed(() => {
  const makerVault = get(vault);
  if (!('totalLiquidated' in makerVault)) {
    return undefined;
  }
  return makerVault.totalLiquidated;
});

const totalInterestOwed = computed(() => {
  const makerVault = get(vault);
  if (!('totalInterestOwed' in makerVault)) {
    return Zero;
  }
  return makerVault.totalInterestOwed;
});
const dai: string = assetSymbolToIdentifierMap.DAI;
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

  :deep() {
    .v-card {
      &__text {
        display: flex;
        flex-direction: column;
      }
    }
  }
}
</style>
