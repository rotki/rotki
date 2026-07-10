<script setup lang="ts">
definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.onchain', icon: 'lu-onchain', section: 1, order: 50, drawer: 'onchain' },
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
