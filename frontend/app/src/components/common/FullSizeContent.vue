<script setup lang="ts">
const wrapper = ref();
const topOffset = ref<number>(0);

useResizeObserver(wrapper, (a) => {
  if (a.length > 0)
    set(topOffset, a[0].contentRect.top + 156);
});

onMounted(() => {
  if (get(wrapper))
    set(topOffset, get(wrapper).offsetTop + 156);
});
</script>

<template>
  <div
    ref="wrapper"
    class="flex flex-col items-center justify-center text-center p-2"
    :style="{
      height: `calc(100vh - ${topOffset}px)`,
    }"
  >
    <slot />
  </div>
</template>
