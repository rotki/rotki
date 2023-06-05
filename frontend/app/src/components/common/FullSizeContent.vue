<script setup lang="ts">
const top = ref(0);
const proxy = useProxy();

onMounted(() => {
  const { top: topBound } = proxy.$el.getBoundingClientRect();
  set(top, topBound);
});

const { xs } = useDisplay();
const css = useCssModule();
</script>

<template>
  <div
    class="d-flex flex-column align-center"
    :class="{
      [css.empty]: true,
      'pa-2 mt-2': xs
    }"
    :style="`height: calc(100vh - ${top + 64}px);`"
  >
    <slot />
  </div>
</template>

<style module lang="scss">
.empty {
  height: 100%;
}
</style>
