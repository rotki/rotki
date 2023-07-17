<script setup lang="ts">
import { BigNumber } from '@rotki/common';

defineProps({
  price: {
    required: true,
    type: BigNumber
  },
  asset: {
    required: true,
    type: String
  }
});

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
