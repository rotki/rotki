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
    class="absolute py-1.5 px-3 rounded-md pointer-events-none whitespace-nowrap leading-5 transition-opacity bg-white dark:bg-black drop-shadow-[0_0_0.5rem_rgba(var(--rui-grey-400))] dark:drop-shadow-[0_0_0.5rem_rgba(var(--rui-grey-800))]"
    :class="tooltipOption.visible ? 'opacity-90 visible' : 'opacity-0 invisible'"
    :style="{
      left: `${tooltipOption.x}px`,
      top: `${tooltipOption.y}px`,
    }"
  >
    <slot />
  </div>
</template>
