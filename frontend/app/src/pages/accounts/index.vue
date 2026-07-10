<script setup lang="ts">
definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.accounts', icon: 'lu-wallet', section: 1, order: 20, drawer: 'accounts' },
  },
  redirect: '/accounts/evm',
});
</script>

<template>
  <RouterView />
</template>
