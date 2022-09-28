<template>
  <stat-card :title="tc('loan_stake.title')">
    <loan-row medium :title="tc('loan_stake.stake')">
      <balance-display :asset="stake.asset" :value="stake" />
    </loan-row>
  </stat-card>
</template>

<script setup lang="ts">
import { AssetBalance } from '@rotki/common';
import { PropType } from 'vue';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import StatCard from '@/components/display/StatCard.vue';

defineProps({
  stake: {
    required: true,
    type: Object as PropType<AssetBalance>
  }
});

const { tc } = useI18n();
</script>
