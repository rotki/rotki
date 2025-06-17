<script setup lang="ts">
import type { TooltipData } from '@/composables/graphs';

withDefaults(
  defineProps<{
    tooltipOption?: TooltipData;
  }>(),
  {
    tooltipOption: undefined,
  },
);

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <div
    v-if="tooltipOption"
    :class="[
      $style.tooltip,
      {
        [$style.tooltip__show]: tooltipOption.visible,
      },
    ]"
    :style="{
      left: `${tooltipOption.x}px`,
      top: `${tooltipOption.y}px`,
    }"
  >
    <slot />
  </div>
</template>

<style module lang="scss">
.tooltip {
  @apply bg-white absolute opacity-0 invisible py-1.5 px-3 rounded-md pointer-events-none whitespace-nowrap leading-5 transition-opacity;
  filter: drop-shadow(0 0 0.5rem rgba(var(--rui-grey-400)));

  &__show {
    @apply opacity-90 visible;
  }
}

:global(.dark) {
  .tooltip {
    @apply bg-black;
    filter: drop-shadow(0 0 0.5rem rgba(var(--rui-grey-800)));
  }
}
</style>
