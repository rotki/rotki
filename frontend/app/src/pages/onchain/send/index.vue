<script setup lang="ts">
import { msg } from '@/message-key';
import TradeSendCard from '@/modules/wallet/send/TradeSendCard.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.onchain_sub.send'), icon: 'lu-send', parent: '/onchain/', order: 10, drawer: 'onchain-send' },
  },
});

defineOptions({
  name: 'OnChainSend',
});
</script>

<template>
  <div class="container !max-w-[520px]">
    <TradeSendCard />
  </div>
</template>
