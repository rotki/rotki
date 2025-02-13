<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    tag?: string;
    height?: string;
    width?: string;
    circle?: boolean;
    padding?: string;
  }>(),
  {
    circle: false,
    height: 'auto',
    padding: '2px',
    tag: 'div',
    width: 'auto',
  },
);

const { isDark } = useRotkiTheme();

const { circle, padding } = toRefs(props);

const radius = computed(() => (get(circle) ? '50%' : '6px'));
</script>

<template>
  <Component
    :is="tag"
    class="wrapper flex"
    :class="{ 'wrapper--inverted': isDark }"
    v-bind="$attrs"
    :style="{ width, height }"
  >
    <slot />
  </Component>
</template>

<style scoped lang="scss">
.wrapper {
  padding: v-bind(padding);

  &--inverted {
    background: white;
    border-radius: v-bind(radius);
  }
}
</style>
