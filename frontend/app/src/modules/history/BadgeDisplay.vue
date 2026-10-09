<script setup lang="ts">
type Color = 'grey' | 'red' | 'green' | 'orange';
const {
  color = 'grey',
} = defineProps<{
  color?: Color;
}>();

defineSlots<{
  default: () => any;
}>();

const colorVariants: Record<Color, string> = {
  green: 'text-green-700 bg-green-100',
  grey: 'text-rui-grey-700 bg-rui-grey-100 dark:text-rui-grey-400 dark:bg-rui-grey-800',
  orange: 'text-orange-700 bg-orange-100',
  red: 'text-red-700 bg-red-100',
};
</script>

<template>
  <div
    :class="colorVariants[color || 'grey']"
    class="font-black rounded-sm px-2 text-overline inline-flex"
  >
    <slot />
  </div>
</template>
