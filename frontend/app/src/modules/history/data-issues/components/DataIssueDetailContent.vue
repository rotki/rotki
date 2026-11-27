<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { RemediationTimelineItem } from '@/modules/history/data-issues/types';
import type { RemediationRequest } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import DataIssueAuditSection from '@/modules/history/data-issues/components/DataIssueAuditSection.vue';
import DataIssueBalanceDivergence from '@/modules/history/data-issues/components/DataIssueBalanceDivergence.vue';
import DataIssueDetailFooter from '@/modules/history/data-issues/components/DataIssueDetailFooter.vue';
import DataIssueDetailHeader from '@/modules/history/data-issues/components/DataIssueDetailHeader.vue';
import DataIssueDetailSummary from '@/modules/history/data-issues/components/DataIssueDetailSummary.vue';
import DataIssueRemediationTimeline from '@/modules/history/data-issues/components/DataIssueRemediationTimeline.vue';
import { toTimelineItems } from '@/modules/history/data-issues/transforms';
import { dataIssueDivergenceKey } from '@/modules/history/data-issues/use-data-issue-divergence-store';

/**
 * One issue's detail body, shared by both of its containers: the drawer on the data-issues page and
 * the bottom sheet in the pinned rail. Owns no open state, emitting `close` for each to interpret.
 */
const { issue, busy = false, failure } = defineProps<{
  issue?: DataIssue;
  busy?: boolean;
  /** The last failed dismiss or retry on the issue shown, passed on to the footer that names it. */
  failure?: InstanceType<typeof DataIssueDetailFooter>['$props']['failure'];
}>();

const emit = defineEmits<{
  close: [];
  dismiss: [id: number];
  remediate: [request: RemediationRequest];
  reopen: [id: number];
  retry: [id: number];
  resolve: [id: number];
  review: [item: RemediationTimelineItem];
}>();

const { t } = useI18n({ useScope: 'global' });

const timeline = computed<RemediationTimelineItem[]>(() => (issue ? toTimelineItems(issue) : []));
</script>

<template>
  <div
    v-if="issue"
    class="flex flex-col h-full"
  >
    <DataIssueDetailHeader
      :issue="issue"
      @close="emit('close')"
    />

    <div class="flex flex-col p-4 overflow-y-auto grow between:border-t between:border-rui-divider between:mt-4 between:pt-4">
      <DataIssueDetailSummary
        :issue="issue"
        :busy="busy"
        @close="emit('close')"
        @remediate="emit('remediate', $event)"
      />

      <DataIssueBalanceDivergence
        :key="dataIssueDivergenceKey(issue)"
        :issue="issue"
        :busy="busy"
        @navigate="emit('close')"
      />

      <p
        v-if="timeline.length === 0"
        class="mt-3! border-t-0! pt-0! text-xs text-rui-text-secondary"
        data-testid="data-issue-no-attempts"
      >
        {{ t('data_issues.detail.no_attempts') }}
      </p>
      <section
        v-else
        class="flex flex-col gap-2"
      >
        <h3 class="text-xs font-medium text-rui-text-secondary">
          {{ t('data_issues.detail.remediation_history') }}
        </h3>
        <DataIssueRemediationTimeline
          :items="timeline"
          @review="emit('review', $event)"
        />
      </section>

      <DataIssueAuditSection :issue="issue" />
    </div>

    <DataIssueDetailFooter
      :issue="issue"
      :busy="busy"
      :failure="failure"
      @dismiss="emit('dismiss', $event)"
      @reopen="emit('reopen', $event)"
      @retry="emit('retry', $event)"
      @resolve="emit('resolve', $event)"
    />
  </div>
</template>
