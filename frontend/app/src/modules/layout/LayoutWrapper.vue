<script setup lang="ts">
import AuthLayout from '@/layouts/auth.vue';
import DefaultLayout from '@/layouts/default.vue';
import PlainLayout from '@/layouts/plain.vue';

const layouts = {
  auth: AuthLayout,
  default: DefaultLayout,
  plain: PlainLayout,
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
