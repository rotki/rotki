<script setup lang="ts">
import { type IssueState, STATE_META } from '@/modules/history/data-issues/constants';
import { useDataIssuesFormat } from '@/modules/history/data-issues/use-data-issues-format';

const { state } = defineProps<{
  state: IssueState;
}>();

const { stateLabel } = useDataIssuesFormat();

const meta = computed(() => STATE_META[state]);
</script>

<template>
  <RuiChip
    size="sm"
    variant="outlined"
    :color="meta.color"
    data-testid="data-issue-state-chip"
  >
    <div class="flex items-center gap-1.5">
      <RuiIcon
        :name="meta.icon"
        size="14"
        :class="{ 'animate-spin': meta.busy }"
      />
      <span>{{ stateLabel(state) }}</span>
    </div>
  </RuiChip>
</template>
