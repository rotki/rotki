<script setup lang="ts">
import { type PropType } from 'vue';
import { type AaveLoan } from '@/types/defi/lending';

const props = defineProps({
  loan: {
    required: true,
    type: Object as PropType<AaveLoan>
  }
});

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
    <VDivider class="my-4" />
    <LoanRow
      v-if="loan.collateral.length > 0"
      :title="t('loan_collateral.per_asset')"
    >
      <VRow
        v-for="collateral in loan.collateral"
        :key="collateral.asset"
        no-gutters
      >
        <VCol>
          <BalanceDisplay :asset="collateral.asset" :value="collateral" />
        </VCol>
      </VRow>
    </LoanRow>
    <VDivider v-if="loan.collateral.length > 0" class="my-4" />

    <LoanRow :title="t('loan_collateral.stable_apr')" class="mb-2">
      <PercentageDisplay :value="loan.stableApr ? loan.stableApr : null" />
    </LoanRow>
    <LoanRow :title="t('loan_collateral.variable_apr')">
      <PercentageDisplay :value="loan.variableApr ? loan.variableApr : null" />
    </LoanRow>
  </StatCard>
</template>
