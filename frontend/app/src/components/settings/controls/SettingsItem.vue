<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});
</script>

<template>
  <div
    v-if="$slots.title || $slots.subtitle"
    v-bind="$attrs"
    class="flex flex-col md:flex-row py-4 md:py-6 gap-4 md:gap-8 lg:gap-12 border-b border-default"
  >
    <div class="w-full md:w-[150px] lg:w-[200px] xl:w-[288px] shrink-0">
      <div
        v-if="$slots.title"
        class="font-medium"
      >
        <slot name="title" />
      </div>
      <div
        v-if="$slots.subtitle"
        class="text-rui-text-secondary text-sm"
      >
        <slot name="subtitle" />
      </div>
    </div>
    <div class="flex-1 min-w-0">
      <slot />
    </div>
  </div>
  <slot v-else />
</template>
