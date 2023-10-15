<script setup lang="ts">
import { type AssetBalance, type BigNumber } from '@rotki/common';

withDefaults(
  defineProps<{
    collateral: AssetBalance;
    ratio?: BigNumber | null;
  }>(),
  {
    ratio: null
  }
);

const { t } = useI18n();
</script>

<template>
  <StatCard :title="t('loan_collateral.title')">
    <LoanRow medium :title="t('loan_collateral.locked_collateral')">
      <BalanceDisplay :asset="collateral.asset" :value="collateral" />
    </LoanRow>

    <div v-if="ratio" class="my-4 border-b" />

    <LoanRow v-if="ratio" :title="t('loan_collateral.ratio')">
      <PercentageDisplay v-if="ratio" :value="ratio.toFormat(2)" />
    </LoanRow>
  </StatCard>
</template>
