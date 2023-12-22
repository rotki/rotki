<script setup lang="ts">
import { type StyleValue } from 'vue/types/jsx';

defineOptions({
  inheritAttrs: false
});

const props = withDefaults(
  defineProps<{
    variant?: 'default' | 'outlined';
    height?: string | number;
  }>(),
  {
    variant: 'outlined',
    height: undefined
  }
);

const css = useCssModule();
const attrs = useAttrs();

const style = computed<StyleValue | undefined>(() => {
  if (!props.height) {
    return undefined;
  }
  return {
    height: toRem(props.height)
  };
});
</script>

<template>
  <div
    :class="[
      css.table,
      {
        [css.outlined]: variant === 'outlined'
      }
    ]"
    :style="style"
    v-bind="attrs"
  >
    <table>
      <slot />
    </table>
  </div>
</template>

<style module lang="scss">
.table {
  @apply w-full;

  table {
    @apply w-full;
  }

  &.outlined {
    @apply border rounded-md border-rui-grey-200;
  }

  thead {
    @apply border-b w-full border-rui-grey-200;
  }

  th {
    @apply font-medium text-sm text-rui-text-secondary text-start;
  }

  th,
  td {
    @apply py-2 px-4;
  }
}

:global(.dark) {
  .table {
    &.outlined,
    thead {
      @apply border-rui-grey-800;
    }
  }
}
</style>
