<script setup lang="ts">
const { count, exitable = false } = defineProps<{
  /** How many rows are selected. */
  count: number;
  /** A selection mode the user switched on, so the bar offers its way back out. */
  exitable?: boolean;
}>();

const emit = defineEmits<{
  clear: [];
  exit: [];
}>();

defineSlots<{
  'default'?: () => any;
  /** Widens the selection past what the count says, such as to every row matching the filters. */
  'scope'?: () => any;
  'select-all'?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    role="toolbar"
    :aria-label="t('table_selection.label')"
    class="flex flex-wrap items-center gap-2 min-h-9.5 rounded-md bg-rui-primary/10 dark:bg-rui-primary/20 pl-3 pr-1 py-0.5"
    data-testid="table-selection-bar"
  >
    <slot name="select-all" />
    <span
      class="text-body-2 font-medium tabular-nums"
      data-testid="table-selection-count"
    >
      {{ t('table_selection.count', { count }) }}
    </span>
    <RuiButton
      v-if="count > 0"
      variant="text"
      size="sm"
      color="primary"
      data-testid="table-selection-clear"
      @click="emit('clear')"
    >
      {{ t('common.actions.clear_selection') }}
    </RuiButton>
    <slot name="scope" />
    <template v-if="$slots.default">
      <RuiDivider
        vertical
        class="h-5 mx-1"
      />
      <div class="flex flex-wrap items-center gap-2">
        <slot />
      </div>
    </template>
    <RuiButton
      v-if="exitable"
      variant="text"
      size="sm"
      class="ml-auto"
      data-testid="table-selection-exit"
      @click="emit('exit')"
    >
      {{ t('common.actions.done') }}
    </RuiButton>
  </div>
</template>
