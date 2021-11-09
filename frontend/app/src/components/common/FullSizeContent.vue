<template>
  <div
    class="d-flex flex-column align-center"
    :class="{
      [$style.empty]: true,
      'pa-2 mt-2': $vuetify.breakpoint.xsOnly
    }"
    :style="`height: calc(100vh - ${top + 64}px);`"
  >
    <slot />
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref } from '@vue/composition-api';
import { useProxy } from '@/composables/common';

export default defineComponent({
  name: 'FullSizeContent',
  setup() {
    const top = ref(0);
    const proxy = useProxy();
    onMounted(() => {
      const { top: topBound } = proxy.$el.getBoundingClientRect();
      top.value = topBound;
    });

    return {
      top
    };
  }
});
</script>

<style module lang="scss">
.empty {
  height: 100%;
}
</style>
