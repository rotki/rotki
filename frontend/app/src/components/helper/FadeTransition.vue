<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});
</script>

<template>
  <TransitionGroup
    enter-class="h-0 opacity-0"
    enter-to-class="h-full opacity-1"
    enter-active-class="transition duration-300"
    leave-class="h-full opacity-1"
    leave-to-class="h-0 opacity-0"
    leave-active-class="transition duration-100"
    v-bind="$attrs"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <slot />
  </TransitionGroup>
</template>
