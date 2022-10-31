<template>
  <component
    :is="component"
    class="wrapper"
    :class="{ 'wrapper--inverted': dark }"
    v-bind="$attrs"
    :style="{ width, height }"
  >
    <slot />
  </component>
</template>
<script setup lang="ts">
import { useTheme } from '@/composables/common';

const props = defineProps({
  component: { required: false, type: String, default: 'div' },
  height: { required: false, type: String, default: 'auto' },
  width: { required: false, type: String, default: 'auto' },
  circle: { required: false, type: Boolean, default: false },
  padding: { required: false, type: String, default: '2px' }
});

const { dark } = useTheme();

const { circle, padding } = toRefs(props);

const radius = computed(() => (get(circle) ? '50%' : '4px'));
</script>
<style scoped lang="scss">
.wrapper {
  padding: v-bind(padding);

  &--inverted {
    background: white;
    border-radius: v-bind(radius);
  }
}
</style>
