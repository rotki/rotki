<script setup lang="ts">
import {
  provideTableSelectionAsk,
  provideTableSelectionCollapsed,
  type SelectionQuestion,
  useSelectionBarCollapse,
} from '@/modules/core/table/table-selection-collapse';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

interface PendingQuestion {
  question: SelectionQuestion;
  onAccept: () => void;
}

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

const menuOpen = ref<boolean>(false);
const pending = shallowRef<PendingQuestion>();

const bar = useTemplateRef<HTMLDivElement>('bar');

const collapsed = useSelectionBarCollapse(bar, () => !!slots.default);

provideTableSelectionCollapsed(collapsed);

provideTableSelectionAsk((question: SelectionQuestion, onAccept: () => void): void => {
  set(pending, { onAccept, question });
});

function acceptPending(): void {
  const asked = get(pending);
  set(pending, undefined);
  set(menuOpen, false);
  asked?.onAccept();
}

watch(menuOpen, (open) => {
  if (!open)
    set(pending, undefined);
});
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
        v-model="menuOpen"
        :options="{ placement: 'bottom-start' }"
        :role="pending ? 'dialog' : undefined"
        :close-on-content-click="!pending"
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
        <InlineConfirm
          v-if="pending"
          class="w-72"
          layout="panel"
          tone="error"
          :title="pending.question.title"
          :message="pending.question.message"
          :confirm-label="pending.question.confirmLabel"
          data-testid="table-selection-confirm"
          @cancel="pending = undefined"
          @confirm="acceptPending()"
        />
        <div
          v-show="!pending"
          class="flex flex-col py-1"
          data-testid="table-selection-entries"
        >
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
