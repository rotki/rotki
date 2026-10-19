<script setup lang="ts">
import { provideTableSelectionCollapsed, useSelectionBarCollapse } from '@/modules/core/table/table-selection-collapse';

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

/**
 * The default slot holds the bulk actions. Build them from `TableSelectionAction`, which turns
 * into a menu entry when the bar is too narrow to show them in a row.
 */
const slots = defineSlots<{
  'default'?: () => any;
  /** Widens the selection past what the count says, such as to every row matching the filters. */
  'scope'?: () => any;
  'select-all'?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const bar = useTemplateRef<HTMLDivElement>('bar');

const collapsed = useSelectionBarCollapse(bar, () => !!slots.default);

provideTableSelectionCollapsed(collapsed);
</script>

<template>
  <div
    ref="bar"
    role="toolbar"
    :aria-label="t('table_selection.label')"
    class="flex items-center gap-2 min-w-0 min-h-9.5 whitespace-nowrap rounded-md bg-rui-primary/10 dark:bg-rui-primary/20 pl-3 pr-1 py-0.5"
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
      <RuiMenu
        v-if="collapsed"
        :options="{ placement: 'bottom-start' }"
        close-on-content-click
      >
        <template #activator="{ attrs }">
          <RuiButton
            size="sm"
            variant="outlined"
            data-testid="table-selection-actions"
            v-bind="attrs"
          >
            {{ t('table_selection.actions') }}
            <template #append>
              <RuiIcon
                name="lu-chevron-down"
                size="16"
              />
            </template>
          </RuiButton>
        </template>
        <div class="flex flex-col py-1">
          <slot />
        </div>
      </RuiMenu>
      <div
        v-else
        class="flex items-center gap-2"
      >
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
