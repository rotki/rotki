<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});
</script>

<template>
  <TransitionGroup
    enter-from-class="h-0 opacity-0"
    enter-to-class="h-full opacity-1"
    enter-active-class="transition duration-300"
    leave-from-class="h-full opacity-1"
    leave-to-class="h-0 opacity-0"
    leave-active-class="transition duration-100"
    v-bind="$attrs"
  >
    <slot />
  </TransitionGroup>
</template>
