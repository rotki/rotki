<script lang="ts" setup>
import ExchangeSummary from './ExchangeSummary.vue';
import BlockchainSummary from './BlockchainSummary.vue';
import ManualSummary from './ManualSummary.vue';
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 w-full">
    <ExchangeSummary />
    <BlockchainSummary />
    <ManualSummary />
  </div>
</template>
