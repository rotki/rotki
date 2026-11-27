<script setup lang="ts">
import type { RemediationRequest } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import type { IssueGroup } from '@/modules/reports/use-report-readiness';
import { RuiChip, RuiProgress } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import ReportReadinessIssueRow from '@/modules/reports/ReportReadinessIssueRow.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const { busy = false, error, groups, loading = false } = defineProps<{
  groups: IssueGroup[];
  loading?: boolean;
  busy?: boolean;
  error?: unknown;
}>();

const emit = defineEmits<{
  action: [request: RemediationRequest];
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="mt-3 border-t border-rui-divider pt-3 flex flex-col gap-3"
    data-testid="report-readiness-checklist"
  >
    <FailureStrip
      v-if="error"
      :title="t('profit_loss_report.readiness.checklist_error')"
      :failure="error"
      data-testid="report-readiness-checklist-error"
      @retry="emit('retry')"
    />

    <div
      v-else-if="loading && groups.length === 0"
      class="flex items-center justify-center py-4"
      data-testid="report-readiness-checklist-loading"
    >
      <RuiProgress
        variant="indeterminate"
        circular
        size="24"
        thickness="2"
        color="primary"
      />
    </div>

    <div
      v-for="group in groups"
      :key="group.kind"
      class="rounded-rui-card border border-rui-divider bg-rui-surface overflow-hidden"
      data-testid="report-readiness-group"
      :data-kind="group.kind"
    >
      <div class="flex items-center justify-between gap-2 px-3 py-2 bg-rui-grey-50 dark:bg-rui-grey-900 border-b border-rui-divider">
        <DataIssueKindChip :kind="group.kind" />
        <RuiChip
          size="sm"
          variant="tonal"
          class="tabular-nums"
          data-testid="report-readiness-group-count"
        >
          {{ group.totalCount }}
        </RuiChip>
      </div>
      <ul class="divide-y divide-rui-divider">
        <ReportReadinessIssueRow
          v-for="issue in group.issues"
          :key="issue.id"
          :issue="issue"
          :busy="busy"
          @action="emit('action', $event)"
        />
      </ul>
    </div>
  </div>
</template>
