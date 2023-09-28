<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    color?: 'grey' | 'red' | 'green';
  }>(),
  {
    color: 'grey'
  }
);

const colorVariants: Record<typeof props.color, string> = {
  grey: 'text-rui-grey-600 bg-rui-grey-100',
  red: 'text-rui-red-600 bg-rui-red-100',
  green: 'text-green-600 bg-rui-green-100'
};
</script>

<template>
  <div
    :class="colorVariants[color]"
    class="font-black rounded py-[0.15rem] px-2 text-overline"
  >
    <slot />
  </div>
</template>
