<script setup lang="ts">
import type { StyleValue } from 'vue';
import { toRem } from '@/utils/data';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    variant?: 'default' | 'outlined';
    height?: string | number;
  }>(),
  {
    height: undefined,
    variant: 'outlined',
  },
);

defineSlots<{
  default: () => any;
}>();

const style = computed<StyleValue | undefined>(() => {
  if (!props.height)
    return undefined;

  return {
    height: toRem(props.height),
  };
});
</script>

<template>
  <div
    class="w-full overflow-y-auto"
    :class="{
      'border rounded-md border-rui-grey-200 dark:border-rui-grey-800': variant === 'outlined',
    }"
    :style="style"
    v-bind="$attrs"
  >
    <table class="w-full [&_th]:py-2 [&_th]:px-4 [&_td]:py-2 [&_td]:px-4 [&_thead]:border-b [&_thead]:w-full [&_thead]:border-rui-grey-200 dark:[&_thead]:border-rui-grey-800 [&_thead_th]:font-medium [&_thead_th]:text-sm [&_thead_th]:text-rui-text-secondary [&_thead_th]:text-start [&_tbody_td]:!border-b-0">
      <slot />
    </table>
  </div>
</template>
