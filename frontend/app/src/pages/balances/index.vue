<script setup lang="ts">
definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.balances', icon: 'lu-balances', section: 1, order: 30, drawer: 'balances' },
  },
  redirect: '/balances/blockchain',
});
</script>

<template>
  <RouterView />
</template>
