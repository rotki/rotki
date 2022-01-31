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
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { setupThemeCheck } from '@/composables/common';

export default defineComponent({
  name: 'AdaptiveWrapper',
  props: {
    component: { required: false, type: String, default: 'div' },
    height: { required: false, type: String, default: 'auto' },
    width: { required: false, type: String, default: 'auto' }
  },
  setup() {
    const { dark } = setupThemeCheck();

    return {
      dark
    };
  }
});
</script>
<style scoped lang="scss">
.wrapper {
  padding: 2px;

  &--inverted {
    background: white;
    border-radius: 4px;
  }
}
</style>
