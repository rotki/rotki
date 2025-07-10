<script setup lang="ts">
import TradeSendCard from '@/modules/onchain/send/TradeSendCard.vue';

defineOptions({
  name: 'OnChainSend',
});
</script>

<template>
  <div class="container !max-w-[520px]">
    <TradeSendCard />
  </div>
</template>
