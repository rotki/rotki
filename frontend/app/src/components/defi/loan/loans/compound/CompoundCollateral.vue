<script setup lang="ts">
import { type CompoundLoan } from '@/types/defi/compound';

const props = defineProps<{
  loan: CompoundLoan;
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

    <div class="my-4 border-b" />

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

    <div v-if="loan.collateral.length > 0" class="my-4 border-b" />

    <LoanRow :title="t('loan_collateral.apy')">
      <PercentageDisplay :value="loan.apy ? loan.apy : null" />
    </LoanRow>
  </StatCard>
</template>
