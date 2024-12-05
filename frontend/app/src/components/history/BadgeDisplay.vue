<script setup lang="ts">
type Color = 'grey' | 'red' | 'green';
withDefaults(defineProps<{
  color?: Color;
}>(), {
  color: 'grey',
});

const colorVariants: Record<Color, string> = {
  green: 'text-rui-green-700 bg-rui-green-100',
  grey: 'text-rui-grey-700 bg-rui-grey-100 dark:text-rui-grey-400 dark:bg-rui-grey-800',
  red: 'text-rui-red-700 bg-rui-red-100',
};
</script>

<template>
  <div
    :class="colorVariants[color || 'grey']"
    class="font-black rounded px-2 text-overline inline-flex"
  >
    <slot />
  </div>
</template>
