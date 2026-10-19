<script setup lang="ts">
/**
 * How the total row sits in its table: `default` pads its cells like a body row, `bordered` sets it
 * off with a top border and roomier cells (the dashboard tables), `fixed` matches a table whose body
 * rows are 44px tall.
 */
type RowAppendVariant = 'default' | 'bordered' | 'fixed';

const {
  isMobile = false,
  label = '',
  labelColspan = 1,
  leftPatchColspan = 0,
  rightPatchColspan = 0,
  variant = 'default',
} = defineProps<{
  label?: string;
  labelColspan?: string | number;
  leftPatchColspan?: string | number;
  rightPatchColspan?: string | number;
  isMobile?: boolean;
  variant?: RowAppendVariant;
}>();

defineSlots<{
  'label': () => any;
  'custom-columns': () => any;
  'default': () => any;
}>();

const VARIANT_CLASSES: Record<RowAppendVariant, string> = {
  default: '[&>td]:py-2',
  bordered: 'border-t border-default [&>td]:py-3',
  fixed: '[&>td]:h-11',
};

const leftColspan = useToNumber(() => leftPatchColspan);
const rightColspan = useToNumber(() => rightPatchColspan);
</script>

<template>
  <tr
    class="font-medium append-row hover:bg-transparent text-sm [&>td]:px-4"
    :class="[VARIANT_CLASSES[variant], { 'flex justify-between': isMobile }]"
  >
    <td
      v-if="leftColspan >= 1 && !isMobile"
      :colspan="leftColspan"
    />
    <td
      :colspan="labelColspan"
      :class="{ 'flex items-center': isMobile }"
    >
      <slot name="label">
        {{ label }}
      </slot>
    </td>
    <slot name="custom-columns" />
    <td
      v-if="$slots.default"
      class="text-end"
      :class="{ 'flex items-center': isMobile }"
    >
      <slot />
    </td>
    <td
      v-if="rightColspan >= 1 && !isMobile"
      :colspan="rightColspan"
    />
  </tr>
</template>
