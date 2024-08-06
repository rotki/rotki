<script setup lang="ts">
definePage({
  redirect: '/user/login',
  meta: {
    layout: 'auth',
  },
});
</script>

<template>
  <RouterView />
</template>
