<template>
  <stat-card :title="tc('loan_collateral.title')">
    <loan-row medium :title="tc('loan_collateral.locked_collateral')">
      <balance-display :asset="collateral.asset" :value="collateral" />
    </loan-row>

    <v-divider v-if="ratio" class="my-4" />

    <loan-row v-if="ratio" :title="tc('loan_collateral.ratio')">
      <percentage-display v-if="ratio" :value="ratio.toFormat(2)" />
    </loan-row>
  </stat-card>
</template>

<script setup lang="ts">
import { AssetBalance, BigNumber } from '@rotki/common';
import { PropType } from 'vue';

import LoanRow from '@/components/defi/loan/LoanRow.vue';
import StatCard from '@/components/display/StatCard.vue';

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

const { tc } = useI18n();
</script>
