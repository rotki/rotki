<script lang="ts" setup>
import BankSummary from './BankSummary.vue';
import BlockchainSummary from './BlockchainSummary.vue';
import ExchangeSummary from './ExchangeSummary.vue';
import ManualSummary from './ManualSummary.vue';
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 w-full">
    <ExchangeSummary />
    <BlockchainSummary />
    <div class="flex flex-col gap-6">
      <BankSummary />
      <ManualSummary />
    </div>
  </div>
</template>
