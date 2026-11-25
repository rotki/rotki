<script setup lang="ts">
import { definePage } from 'vue-router/experimental';

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
