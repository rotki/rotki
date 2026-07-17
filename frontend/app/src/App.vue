<script setup lang="ts">
import AppQuitting from '@/modules/shell/app/AppQuitting.vue';
import { useAppQuitting } from '@/modules/shell/app/use-app-quitting';
import LayoutWrapper from '@/modules/shell/layout/LayoutWrapper.vue';

const { quitting } = useAppQuitting();
</script>

<template>
  <AppQuitting v-if="quitting" />
  <LayoutWrapper v-else>
    <RouterView />
  </LayoutWrapper>
</template>
