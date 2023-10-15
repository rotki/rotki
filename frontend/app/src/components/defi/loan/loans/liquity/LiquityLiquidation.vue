<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

defineProps<{
  price: BigNumber;
  asset: string;
}>();

const { t } = useI18n();
</script>

<template>
  <StatCard :title="t('loan_liquidation.title')">
    <LoanRow medium :title="t('loan_collateral.liquidation_price')">
      <AmountDisplay
        show-currency="ticker"
        fiat-currency="USD"
        :value="price"
        :min-width="18"
      />
    </LoanRow>
  </StatCard>
</template>
