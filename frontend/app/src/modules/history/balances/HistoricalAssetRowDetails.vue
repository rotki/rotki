<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import HistoricalBalancesTable from '@/modules/history/balances/HistoricalBalancesTable.vue';

defineProps<{
  row: AssetBalanceWithPrice;
  loading?: boolean;
  timestamp?: number;
}>();
</script>

<template>
  <div class="rounded-xl my-2">
    <div class="bg-white dark:bg-[#1E1E1E] rounded-xl p-4">
      <HistoricalBalancesTable
        v-if="row.breakdown"
        :balances="row.breakdown"
        :loading="loading"
        :timestamp="timestamp"
      />
    </div>
  </div>
</template>
