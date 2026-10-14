<script setup lang="ts">
import type { TooltipData } from '@/modules/statistics/use-graph-tooltip';

const { tooltipOption } = defineProps<{
  tooltipOption?: TooltipData;
}>();

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <div
    v-if="tooltipOption"
    class="absolute z-10 min-w-40 px-3 py-2 rounded-rui-sm border border-rui-divider bg-rui-surface shadow-rui-menu pointer-events-none whitespace-nowrap text-sm/5 text-rui-text transition-opacity"
    :class="tooltipOption.visible ? 'opacity-100 visible' : 'opacity-0 invisible'"
    :style="{
      left: `${tooltipOption.x}px`,
      top: `${tooltipOption.y}px`,
    }"
  >
    <slot />
  </div>
</template>
