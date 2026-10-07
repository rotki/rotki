<script setup lang="ts">
import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import BalanceDivergenceView from '@/modules/history/balances/BalanceDivergenceView.vue';
import DataIssueBalanceDivergence from '@/modules/history/data-issues/components/DataIssueBalanceDivergence.vue';

const { issue, result } = defineProps<{
  issue?: DataIssue;
  result?: HistoricalBalanceDivergenceResponse;
}>();
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div
      v-if="issue"
      class="flex-1 overflow-y-auto p-4 md:p-6"
      data-testid="balance-divergence-pinned-issue"
    >
      <DataIssueBalanceDivergence
        :key="issue.id"
        :issue="issue"
        :initial-result="result"
      />
    </div>
    <BalanceDivergenceView v-else />
  </div>
</template>
