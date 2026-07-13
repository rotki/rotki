<script setup lang="ts">
import { msg } from '@/message-key';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.onchain'), icon: 'lu-onchain', section: 1, order: 50, drawer: 'onchain' },
  },
  redirect: '/onchain/send',
});

defineOptions({
  name: 'OnChain',
});
</script>

<template>
  <RouterView />
</template>
