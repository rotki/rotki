<script setup lang="ts">
defineSlots<{
  default: () => any;
}>();

const AuthLayout = defineAsyncComponent(() => import('@/layouts/auth.vue'));
const DefaultLayout = defineAsyncComponent(() => import('@/layouts/default.vue'));
const PlainLayout = defineAsyncComponent(() => import('@/layouts/plain.vue'));

const layouts = {
  auth: AuthLayout,
  default: DefaultLayout,
  plain: PlainLayout,
};

function isLayoutName(value: unknown): value is keyof typeof layouts {
  return typeof value === 'string' && value in layouts;
}

const route = useRoute();

const layout = computed(() => {
  const defaultLayout: keyof typeof layouts = route.path === '/' ? 'plain' : 'default';
  const { layout: layoutName } = route.meta;
  return isLayoutName(layoutName) ? layouts[layoutName] : layouts[defaultLayout];
});
</script>

<template>
  <component :is="layout">
    <slot />
  </component>
</template>
