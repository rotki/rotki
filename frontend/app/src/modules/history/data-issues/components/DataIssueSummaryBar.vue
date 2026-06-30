<script setup lang="ts">
import type { StateCounts } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { IssueState, STATE_META } from '@/modules/history/data-issues/constants';
import { useDataIssuesFormat } from '@/modules/history/data-issues/use-data-issues-format';

const { counts, activeStates } = defineProps<{
  counts: StateCounts;
  activeStates: string[];
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

const allClear = computed<boolean>(() => SUMMARY_STATES.every(state => counts[state] === 0));
</script>

<template>
  <div
    class="grid grid-cols-1 sm:grid-cols-3 gap-3"
    data-testid="data-issue-summary"
  >
    <RuiButton
      v-for="card in cards"
      :key="card.state"
      variant="outlined"
      class="!justify-start !p-3 !h-auto"
      :class="{ '!border-rui-primary': card.active }"
      :data-testid="`data-issue-summary-${card.state}`"
      @click="emit('select', card.state)"
    >
      <div class="flex items-center gap-3 w-full">
        <RuiIcon
          :name="card.icon"
          :color="card.color"
          :class="{ 'animate-spin': card.busy && card.count > 0 }"
        />
        <div class="flex flex-col items-start">
          <span class="text-h6 font-medium leading-none">{{ card.count }}</span>
          <span class="text-caption text-rui-text-secondary">{{ card.label }}</span>
        </div>
      </div>
    </RuiButton>

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
