<script setup lang="ts">
import { type Balance } from '@rotki/common';

withDefaults(
  defineProps<{
    debt: Balance;
    asset?: string;
  }>(),
  {
    asset: ''
  }
);

const { t } = useI18n();
</script>

<template>
  <StatCard :title="t('loan_debt.title')" :class="$style.debt">
    <LoanRow :title="t('loan_debt.outstanding_debt')">
      <BalanceDisplay :asset="asset" :value="debt" />
    </LoanRow>
    <slot />
  </StatCard>
</template>

<style module lang="scss">
.debt {
  height: 100%;
}
</style>
