<script setup lang="ts">
import { assetSymbolToIdentifierMap } from '@rotki/common/lib/data';
import { type MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps<{
  vault: MakerDAOVaultModel;
}>();

const assetPadding = 3;

const { vault } = toRefs(props);
const premium = usePremium();
const { t } = useI18n();

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

<template>
  <StatCard :title="t('loan_liquidation.title')" :class="$style.liquidation">
    <div class="pb-5" :class="$style.upper">
      <LoanRow :title="t('loan_liquidation.liquidation_price')">
        <AmountDisplay fiat-currency="USD" :value="vault.liquidationPrice" />
      </LoanRow>

      <div class="my-4 border-b" />

      <LoanRow :title="t('loan_liquidation.minimum_ratio')" :medium="false">
        <PercentageDisplay :value="vault.liquidationRatio" />
      </LoanRow>
    </div>
    <div>
      <span :class="$style.header" class="text-rui-text">
        {{ t('loan_liquidation.liquidation_events') }}
      </span>
      <VSkeletonLoader
        v-if="premium"
        :loading="!liquidated"
        class="mx-auto pt-3"
        max-width="450"
        type="paragraph"
      >
        <div v-if="liquidated && liquidated.amount.gt(0)">
          <div class="mb-2">
            <LoanRow :title="t('loan_liquidation.liquidated_collateral')">
              <AmountDisplay
                :asset-padding="assetPadding"
                :value="liquidated.amount"
                :asset="vault.collateral.asset"
              />
            </LoanRow>
            <LoanRow :medium="false">
              <AmountDisplay
                :asset-padding="assetPadding"
                :value="liquidated.usdValue"
                fiat-currency="USD"
              />
            </LoanRow>
          </div>
          <LoanRow :title="t('loan_liquidation.outstanding_debt')">
            <AmountDisplay
              :asset-padding="assetPadding"
              :value="totalInterestOwed"
              :asset="dai"
            />
          </LoanRow>

          <div class="my-4 border-b" />

          <LoanRow :title="t('loan_liquidation.total_value_lost')">
            <AmountDisplay
              :asset-padding="assetPadding"
              :value="valueLost"
              fiat-currency="USD"
            />
          </LoanRow>
        </div>
        <div v-else v-text="t('loan_liquidation.no_events')" />
      </VSkeletonLoader>
      <div v-else class="text-right">
        <PremiumLock />
      </div>
    </div>
  </StatCard>
</template>

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

  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-card__text) {
    display: flex;
    flex-direction: column;
  }

  /* stylelint-enable selector-class-pattern,selector-nested-pattern */
}
</style>
