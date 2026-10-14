<script setup lang="ts">
import type { StateCounts } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { IssueState, STATE_META } from '@/modules/history/data-issues/constants';
import { useDataIssuesFormat } from '@/modules/history/data-issues/use-data-issues-format';

const { counts, activeStates, failed = false } = defineProps<{
  counts: StateCounts;
  activeStates: string[];
  /** The counts could not be refreshed, so zeros do not mean all clear. */
  failed?: boolean;
}>();

const emit = defineEmits<{
  select: [state: IssueState];
}>();

const { t } = useI18n({ useScope: 'global' });
const { stateLabel } = useDataIssuesFormat();

const SUMMARY_STATES: IssueState[] = [
  IssueState.OPEN,
  IssueState.AUTO_REMEDIATING,
  IssueState.UNRESOLVED,
];

const selectedStates = computed<string[]>(() => activeStates);

const cards = computed(() => SUMMARY_STATES.map((state) => {
  const meta = STATE_META[state];
  return {
    active: get(selectedStates).length === 1 && get(selectedStates)[0] === state,
    busy: meta.busy === true,
    color: meta.color === 'grey' ? undefined : meta.color,
    count: counts[state],
    icon: meta.icon,
    label: stateLabel(state),
    state,
  };
}));

const allClear = computed<boolean>(() => !failed && SUMMARY_STATES.every(state => counts[state] === 0));
</script>

<template>
  <div
    class="grid grid-cols-1 sm:grid-cols-3 gap-4"
    data-testid="data-issue-summary"
  >
    <button
      v-for="card in cards"
      :key="card.state"
      type="button"
      class="flex flex-col items-start gap-1 p-4 text-left rounded-rui-card border bg-rui-surface transition-colors hover:bg-rui-hover focus-visible:outline-2 focus-visible:outline-rui-primary"
      :class="card.active ? 'border-rui-primary ring-1 ring-rui-primary' : 'border-rui-divider'"
      :aria-pressed="card.active"
      data-testid="data-issue-summary-card"
      :data-key="card.state"
      @click="emit('select', card.state)"
    >
      <span class="flex items-center gap-1.5 min-h-6 text-sm text-rui-text-secondary">
        <RuiIcon
          :name="card.icon"
          :color="card.color"
          size="16"
          :class="{ 'animate-spin': card.busy && card.count > 0 }"
        />
        {{ card.label }}
      </span>
      <span class="text-h5 font-semibold text-rui-text">{{ card.count }}</span>
    </button>

    <div
      v-if="allClear"
      class="sm:col-span-3 text-caption text-rui-text-secondary flex items-center gap-1.5"
    >
      <RuiIcon
        name="lu-circle-check"
        color="success"
        size="16"
      />
      {{ t('data_issues.summary.all_clear') }}
    </div>
  </div>
</template>
