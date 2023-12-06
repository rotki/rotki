<script setup lang="ts">
const top = ref(0);
const proxy = useProxy();

onMounted(() => {
  const { top: topBound } = proxy.$el.getBoundingClientRect();
  set(top, topBound);
});
</script>

<template>
  <div
    class="flex flex-col items-center justify-center text-center p-2"
    :style="`height: calc(100vh - ${top + 92}px);`"
  >
    <slot />
  </div>
</template>
