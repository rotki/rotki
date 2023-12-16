<script setup lang="ts">
import { useRotkiTheme } from '@rotki/ui-library';

const props = withDefaults(
  defineProps<{
    tag?: string;
    height?: string;
    width?: string;
    circle?: boolean;
    padding?: string;
  }>(),
  {
    tag: 'div',
    height: 'auto',
    width: 'auto',
    circle: false,
    padding: '2px',
  },
);

const { isDark } = useRotkiTheme();

const { circle, padding } = toRefs(props);

const radius = computed(() => (get(circle) ? '50%' : '4px'));
const attrs = useAttrs();
</script>

<template>
  <Component
    :is="tag"
    class="wrapper flex"
    :class="{ 'wrapper--inverted': isDark }"
    v-bind="attrs"
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
