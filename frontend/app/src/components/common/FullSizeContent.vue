<script setup lang="ts">
const wrapper = ref();
const { top } = useElementBounding(wrapper);
</script>

<template>
  <div
    ref="wrapper"
    class="flex flex-col items-center justify-center text-center p-2"
    :style="`height: calc(100vh - ${top + 92}px);`"
  >
    <slot />
  </div>
</template>
