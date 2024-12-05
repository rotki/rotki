<script setup lang="ts">
definePage({
  meta: {
    layout: 'auth',
  },
  redirect: '/user/login',
});
</script>

<template>
  <RouterView />
</template>
