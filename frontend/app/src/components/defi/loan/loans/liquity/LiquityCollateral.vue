<script setup lang="ts">
import { type AssetBalance, BigNumber } from '@rotki/common';
import { type PropType } from 'vue';

defineProps({
  collateral: {
    required: true,
    type: Object as PropType<AssetBalance>
  },
  ratio: {
    required: false,
    type: BigNumber as PropType<BigNumber | null | undefined>,
    default: null
  }
});

const { t } = useI18n();
</script>

<template>
  <StatCard :title="t('loan_collateral.title')">
    <LoanRow medium :title="t('loan_collateral.locked_collateral')">
      <BalanceDisplay :asset="collateral.asset" :value="collateral" />
    </LoanRow>

    <VDivider v-if="ratio" class="my-4" />

    <LoanRow v-if="ratio" :title="t('loan_collateral.ratio')">
      <PercentageDisplay v-if="ratio" :value="ratio.toFormat(2)" />
    </LoanRow>
  </StatCard>
</template>
