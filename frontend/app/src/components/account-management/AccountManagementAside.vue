<script setup lang="ts">
const css = useCssModule();
</script>

<template>
  <div :class="css.aside">
    <slot />
  </div>
</template>

<style lang="scss" module>
.aside {
  @apply max-w-[31rem] mx-auto lg:max-w-[29%] flex-col flex-grow-0 lg:flex-1 border-b lg:border-l overflow-auto;
}
</style>
