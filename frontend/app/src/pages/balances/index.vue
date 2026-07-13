<script setup lang="ts">
import { msg } from '@/message-key';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances'), icon: 'lu-balances', section: 1, order: 30, drawer: 'balances' },
  },
  redirect: '/balances/blockchain',
});
</script>

<template>
  <RouterView />
</template>
