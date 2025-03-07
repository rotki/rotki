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
    :class="[
      $style.table,
      {
        [$style.outlined]: variant === 'outlined',
      },
    ]"
    :style="style"
    v-bind="$attrs"
  >
    <table>
      <slot />
    </table>
  </div>
</template>

<style module lang="scss">
.table {
  @apply w-full overflow-y-auto;

  table {
    @apply w-full;

    th,
    td {
      @apply py-2 px-4;
    }

    thead {
      @apply border-b w-full border-rui-grey-200;

      th {
        @apply font-medium text-sm text-rui-text-secondary text-start;
      }
    }

    tbody {
      tr {
        td {
          @apply border-b-0 #{!important};
        }
      }
    }
  }

  &.outlined {
    @apply border rounded-md border-rui-grey-200;
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
