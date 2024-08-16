<script setup lang="ts">
import type { AssetBalance, BigNumber } from '@rotki/common';

withDefaults(
  defineProps<{
    collateral: AssetBalance;
    ratio?: BigNumber | null;
  }>(),
  {
    ratio: null,
  },
);

const { balances } = storeToRefs(useLiquityStore());

const { t } = useI18n();
</script>

<template>
  <StatCard :title="t('loan_collateral.title')">
    <LoanRow
      medium
      :title="t('loan_collateral.locked_collateral')"
    >
      <BalanceDisplay
        :asset="collateral.asset"
        :value="collateral"
      />
    </LoanRow>

    <RuiDivider
      v-if="ratio"
      class="my-4"
    />

    <LoanRow
      v-if="ratio"
      :title="t('loan_collateral.ratio')"
    >
      <PercentageDisplay
        v-if="ratio"
        :value="ratio.toFormat(2)"
      />
    </LoanRow>
    <LoanRow v-if="balances.totalCollateralRatio">
      <template #title>
        <div class="flex items-center gap-1">
          {{ t('loan_collateral.total_collateral_ratio') }}
          <ExternalLink
            :url="externalLinks.liquityTotalCollateralRatioDoc"
            custom
          >
            <RuiButton
              icon
              variant="text"
              size="sm"
              class="-my-1"
            >
              <RuiIcon name="question-line" />
            </RuiButton>
          </ExternalLink>
        </div>
      </template>
      <PercentageDisplay
        v-if="balances.totalCollateralRatio"
        :value="balances.totalCollateralRatio.toFormat(2)"
      />
    </LoanRow>
  </StatCard>
</template>
