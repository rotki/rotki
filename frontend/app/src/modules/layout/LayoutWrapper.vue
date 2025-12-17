<script setup lang="ts">
const AuthLayout = defineAsyncComponent(() => import('@/layouts/auth.vue'));
const DefaultLayout = defineAsyncComponent(() => import('@/layouts/default.vue'));
const PlainLayout = defineAsyncComponent(() => import('@/layouts/plain.vue'));

const layouts = {
  auth: AuthLayout,
  default: DefaultLayout,
  plain: PlainLayout,
};

const route = useRoute();

const layout = computed(() => {
  const defaultLayout: keyof typeof layouts = route.path === '/' ? 'plain' : 'default';
  const layoutName = route.meta.layout || defaultLayout;
  return layouts[layoutName as keyof typeof layouts] || layouts[defaultLayout];
});
</script>

<template>
  <component :is="layout">
    <slot />
  </component>
</template>
