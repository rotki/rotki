<template>
  <stat-card :title="tc('loan_stake.title')">
    <div v-if="stakings.length > 0" class="d-flex justify-space-between">
      <div class="grey--text">{{ tc('loan_stake.stake') }}</div>
      <div>
        <div v-for="stake in stakings" :key="stake.asset" class="mb-4">
          <balance-display :asset="stake.asset" :value="stake" />
        </div>
      </div>
    </div>
    <div v-else class="text-center grey--text pt-4">
      {{ tc('loan_stake.no_lqty_staked') }}
    </div>
  </stat-card>
</template>

<script setup lang="ts">
import { type AssetBalance } from '@rotki/common';
import { type PropType } from 'vue';
import StatCard from '@/components/display/StatCard.vue';

defineProps({
  stakings: {
    required: true,
    type: Array as PropType<AssetBalance[]>
  }
});

const { tc } = useI18n();
</script>
