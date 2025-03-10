<script setup lang="ts">
import AuthLayout from '@/layouts/auth.vue';
import DefaultLayout from '@/layouts/default.vue';

const layouts = {
  auth: AuthLayout,
  default: DefaultLayout,
};

const route = useRoute();

const layout = computed(() => {
  const defaultLayout: keyof typeof layouts = route.path === '/' ? 'auth' : 'default';
  const layoutName = route.meta.layout || defaultLayout;
  return layouts[layoutName as keyof typeof layouts] || layouts[defaultLayout];
});
</script>

<template>
  <component :is="layout">
    <slot />
  </component>
</template>
