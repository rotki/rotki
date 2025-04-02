<script lang="ts" setup>
defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <div class="max-w-[31rem] mx-auto lg:max-w-[29%] flex-col grow-0 lg:flex-1 border-b lg:border-b-0 border-default lg:border-l overflow-auto">
    <slot />
  </div>
</template>
