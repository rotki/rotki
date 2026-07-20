<script setup lang="ts">
import type { AssetBalance } from '@rotki/common';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';

const { balances, emptyLabel, loading } = defineProps<{
  balances: AssetBalance[];
  emptyLabel: string;
  loading?: boolean;
}>();
</script>

<template>
  <div v-if="balances.length > 0">
    <div
      v-for="assetBalance in balances"
      :key="assetBalance.asset"
    >
      <BalanceDisplay
        :asset="assetBalance.asset"
        :value="assetBalance"
        :loading="loading"
      />
    </div>
  </div>
  <div
    v-else
    class="text-rui-text-secondary pb-2"
  >
    {{ emptyLabel }}
  </div>
</template>
