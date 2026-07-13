<script setup lang="ts">
import { msg } from '@/message-key';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts'), icon: 'lu-wallet', section: 1, order: 20, drawer: 'accounts' },
  },
  redirect: '/accounts/evm',
});
</script>

<template>
  <RouterView />
</template>
