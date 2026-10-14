<script setup lang="ts">
import type { ConflictResolutionStrategy } from '@/modules/core/common/common-types';

/**
 * One rule property in the conflicts table: the local value over the remote one, on rows as tall as
 * the version buttons beside them. A property the two versions disagree on is tinted, and once a
 * version is chosen the other one fades, so the outcome reads off the table.
 */
defineProps<{
  differs: boolean;
  chosen?: ConflictResolutionStrategy;
}>();

defineSlots<{
  local: () => any;
  remote: () => any;
}>();
</script>

<template>
  <div
    class="w-full flex flex-col"
    :class="{ 'bg-rui-warning/10': differs }"
  >
    <div
      class="h-10 flex items-center justify-center transition-opacity"
      :class="{ 'opacity-40': chosen === 'remote' }"
    >
      <slot name="local" />
    </div>
    <div
      class="h-10 flex items-center justify-center border-t border-rui-divider transition-opacity"
      :class="{ 'opacity-40': chosen === 'local' }"
    >
      <slot name="remote" />
    </div>
  </div>
</template>
