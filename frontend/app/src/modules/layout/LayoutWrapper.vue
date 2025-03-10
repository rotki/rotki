<script setup lang="ts">
import AuthLayout from '@/layouts/auth.vue';
import DefaultLayout from '@/layouts/default.vue';

const layouts = {
  auth: AuthLayout,
  default: DefaultLayout,
};

const route = useRoute();

const layout = computed(() => {
  const layoutName = route.meta.layout || 'default';
  return layouts[layoutName as keyof typeof layouts] || layouts.default;
});
</script>

<template>
  <component :is="layout">
    <slot />
  </component>
</template>
