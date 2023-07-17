<script setup lang="ts">
import { type PropType } from 'vue';
import { type CompoundLoan } from '@/types/defi/compound';

const props = defineProps({
  loan: {
    required: true,
    type: Object as PropType<CompoundLoan>
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

    <LoanRow :title="t('loan_collateral.apy')">
      <PercentageDisplay :value="loan.apy ? loan.apy : null" />
    </LoanRow>
  </StatCard>
</template>
