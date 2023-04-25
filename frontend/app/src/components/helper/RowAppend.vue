<script setup lang="ts">
import { type PropType } from 'vue';

const props = defineProps({
  className: {
    required: false,
    type: [String, Object] as PropType<string | Record<string, any>>,
    default: ''
  },
  label: { required: false, type: String, default: '' },
  labelColspan: { required: false, type: [Number, String], default: 1 },
  leftPatchColspan: { required: false, type: [Number, String], default: 0 },
  isMobile: { required: true, type: Boolean },
  rightPatchColspan: { required: false, type: [Number, String], default: 0 }
});

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
    'd-flex justify-space-between': isMobile.value,
    ...propClassName
  };
});

const leftColspan = useToNumber(leftPatchColspan);
const rightColspan = useToNumber(rightPatchColspan);
</script>

<template>
  <tr class="font-weight-medium append-row" :class="formattedClassName">
    <td v-if="leftColspan >= 1 && !isMobile" :colspan="leftColspan" />
    <td :colspan="labelColspan" :class="{ 'd-flex align-center': isMobile }">
      {{ label }}
    </td>
    <slot name="custom-columns" />
    <td
      v-if="slots.default"
      class="text-end"
      :class="{ 'd-flex align-center': isMobile }"
    >
      <slot />
    </td>
    <td v-if="rightColspan >= 1 && !isMobile" :colspan="rightColspan" />
  </tr>
</template>
<style scoped lang="scss">
.append {
  &-row {
    &:hover {
      background-color: transparent !important;
    }
  }
}
</style>
