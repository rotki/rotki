<script setup lang="ts">
import { type AaveLoan } from '@/types/defi/lending';

const props = defineProps<{
  loan: AaveLoan;
}>();

const { loan } = toRefs(props);
const { t } = useI18n();
const assetPadding = 5;
const totalCollateralUsd = totalCollateral(loan);
</script>

<template>
  <StatCard :title="t('loan_collateral.title')">
    <LoanRow medium :title="t('loan_collateral.locked_collateral')">
      <AmountDisplay
        :asset-padding="assetPadding"
        :value="totalCollateralUsd"
        fiat-currency="USD"
      />
    </LoanRow>

    <RuiDivider class="my-4" />

    <LoanRow
      v-if="loan.collateral.length > 0"
      :title="t('loan_collateral.per_asset')"
    >
      <div
        v-for="collateral in loan.collateral"
        :key="collateral.asset"
        class="flex flex-row"
      >
        <BalanceDisplay :asset="collateral.asset" :value="collateral" />
      </div>
    </LoanRow>

    <RuiDivider v-if="loan.collateral.length > 0" class="my-4" />

    <LoanRow :title="t('loan_collateral.stable_apr')" class="mb-2">
      <PercentageDisplay :value="loan.stableApr" />
    </LoanRow>

    <LoanRow :title="t('loan_collateral.variable_apr')">
      <PercentageDisplay :value="loan.variableApr" />
    </LoanRow>
  </StatCard>
</template>
