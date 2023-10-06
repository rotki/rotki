<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    className?: string | Record<string, any>;
    label?: string;
    labelColspan?: string | number;
    leftPatchColspan?: string | number;
    rightPatchColspan?: string | number;
    isMobile?: boolean;
  }>(),
  {
    className: '',
    label: '',
    labelColspan: 1,
    leftPatchColspan: 0,
    rightPatchColspan: 0,
    isMobile: false
  }
);

const { className, isMobile, leftPatchColspan, rightPatchColspan } =
  toRefs(props);

const slots = useSlots();

const formattedClassName = computed(() => {
  const propClassName =
    typeof className.value === 'object'
      ? className.value
      : {
          [className.value]: true
        };

  return {
    'flex justify-between': isMobile.value,
    ...propClassName
  };
});

const leftColspan = useToNumber(leftPatchColspan);
const rightColspan = useToNumber(rightPatchColspan);
</script>

<template>
  <tr
    class="font-medium append-row hover:bg-transparent"
    :class="formattedClassName"
  >
    <td v-if="leftColspan >= 1 && !isMobile" :colspan="leftColspan" />
    <td :colspan="labelColspan" :class="{ 'flex align-center': isMobile }">
      <slot name="label">
        {{ label }}
      </slot>
    </td>
    <slot name="custom-columns" />
    <td
      v-if="slots.default"
      class="text-end"
      :class="{ 'flex align-center': isMobile }"
    >
      <slot />
    </td>
    <td v-if="rightColspan >= 1 && !isMobile" :colspan="rightColspan" />
  </tr>
</template>
