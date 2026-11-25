<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { RuiButton, RuiChip, RuiIcon } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import DataIssueRemediationModals from '@/modules/history/data-issues/components/DataIssueRemediationModals.vue';
import { useDataIssueRemediationActions } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import ReportReadinessChecklist from '@/modules/reports/ReportReadinessChecklist.vue';
import { useReportReadiness } from '@/modules/reports/use-report-readiness';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const { endTs, startTs } = defineProps<{
  startTs?: number;
  endTs?: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  enabled,
  error,
  groupedIssues,
  issuesError,
  issuesLoading,
  loading,
  modelExpanded,
  readiness,
  refresh,
} = useReportReadiness({
  endTs: () => endTs,
  startTs: () => startTs,
});

const {
  actionFailure,
  busy: actionBusy,
  modelEventForm,
  modelMatchingOpen,
  modelPriceUpdate,
  modelSubModalOpen,
  onModalSaved,
  runRemediation,
} = useDataIssueRemediationActions(refresh);

const status = computed<'ready' | 'stale' | 'blocked'>(() => {
  const current = get(readiness);
  if (!current)
    return 'stale';
  if (current.stale)
    return 'stale';
  if (current.openIssuesCount > 0 || !current.ready)
    return 'blocked';
  return 'ready';
});

const openIssuesCount = computed<number>(() => get(readiness)?.openIssuesCount ?? 0);
const numUnruledEvents = computed<number>(() => get(readiness)?.numUnruledEvents ?? 0);

const accountingRulesRoute: RouteLocationRaw = { name: '/settings/accounting/' };
const allIssuesRoute: RouteLocationRaw = { name: '/history/data-issues/[[tab]]', params: { tab: 'issues' } };
const confirmedIssuesRoute: RouteLocationRaw = {
  name: '/history/data-issues/[[tab]]',
  params: { tab: 'issues' },
  query: { manualOnly: 'true' },
};

const BANNER_BORDER_CLASSES: Record<'ready' | 'stale' | 'blocked', string> = {
  blocked: 'border-rui-warning/50 bg-rui-warning/5',
  ready: 'border-rui-success/40 bg-rui-success/5',
  stale: 'border-rui-warning/40 bg-rui-warning/5',
};

const bannerBorderClass = computed<string>(() => BANNER_BORDER_CLASSES[get(status)]);

function toggleChecklist(): void {
  set(modelExpanded, !get(modelExpanded));
}
</script>

<template>
  <section
    v-if="enabled"
    class="rounded-rui-card border p-4 transition-colors"
    :class="bannerBorderClass"
    data-testid="report-readiness-banner"
    :data-status="status"
  >
    <FailureStrip
      v-if="error"
      :title="t('profit_loss_report.readiness.load_error')"
      :failure="error"
      data-testid="report-readiness-error"
      @retry="refresh()"
    />

    <div
      v-else
      class="flex flex-col gap-2"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2 min-w-0">
          <RuiChip
            v-if="status === 'ready'"
            color="success"
            variant="tonal"
            size="sm"
            data-testid="report-readiness-badge"
          >
            <div class="flex items-center gap-1.5">
              <RuiIcon
                name="lu-shield-check"
                size="14"
              />
              <span>{{ t('profit_loss_report.readiness.ready_badge') }}</span>
            </div>
          </RuiChip>
          <RuiChip
            v-else-if="status === 'stale'"
            color="warning"
            variant="tonal"
            size="sm"
            data-testid="report-readiness-badge"
          >
            <div class="flex items-center gap-1.5">
              <RuiIcon
                name="lu-loader-circle"
                size="14"
                class="animate-spin"
              />
              <span>{{ t('profit_loss_report.readiness.stale_badge') }}</span>
            </div>
          </RuiChip>
          <RuiChip
            v-else
            color="warning"
            variant="tonal"
            size="sm"
            data-testid="report-readiness-badge"
          >
            <div class="flex items-center gap-1.5">
              <RuiIcon
                name="lu-shield-alert"
                size="14"
              />
              <span class="tabular-nums">
                {{ t('profit_loss_report.readiness.blocked_badge', { count: openIssuesCount }, openIssuesCount) }}
              </span>
            </div>
          </RuiChip>

          <span class="text-sm text-rui-text-secondary">
            <template v-if="status === 'ready'">
              {{ t('profit_loss_report.readiness.ready_hint') }}
            </template>
            <template v-else-if="status === 'stale'">
              {{ t('profit_loss_report.readiness.stale_hint') }}
            </template>
            <template v-else>
              {{ t('profit_loss_report.readiness.blocked_hint') }}
            </template>
          </span>

          <RouterLink
            v-if="numUnruledEvents > 0"
            :to="accountingRulesRoute"
            class="inline-flex"
            data-testid="report-readiness-unruled-pill"
          >
            <RuiChip
              color="info"
              variant="outlined"
              size="sm"
              class="cursor-pointer hover:bg-rui-info/10"
            >
              <div class="flex items-center gap-1.5">
                <RuiIcon
                  name="lu-info"
                  size="14"
                />
                <span class="tabular-nums">
                  {{ t('profit_loss_report.readiness.unruled_events', { count: numUnruledEvents }, numUnruledEvents) }}
                </span>
              </div>
            </RuiChip>
          </RouterLink>
        </div>

        <div class="flex flex-wrap items-center gap-2 shrink-0">
          <RouterLink :to="confirmedIssuesRoute">
            <RuiButton
              variant="text"
              size="sm"
              data-testid="report-readiness-confirmed-link"
            >
              {{ t('profit_loss_report.readiness.view_confirmed') }}
            </RuiButton>
          </RouterLink>
          <RouterLink :to="allIssuesRoute">
            <RuiButton
              variant="text"
              size="sm"
              data-testid="report-readiness-inbox-link"
            >
              {{ t('data_issues.panel.view_all') }}
            </RuiButton>
          </RouterLink>
          <RuiButton
            v-if="openIssuesCount > 0"
            variant="outlined"
            color="primary"
            size="sm"
            :aria-expanded="modelExpanded"
            data-testid="report-readiness-toggle"
            @click="toggleChecklist()"
          >
            {{ modelExpanded ? t('profit_loss_report.readiness.hide_checklist') : t('profit_loss_report.readiness.review_issues') }}
            <template #append>
              <RuiIcon
                :name="modelExpanded ? 'lu-chevron-up' : 'lu-chevron-down'"
                size="16"
              />
            </template>
          </RuiButton>
          <RuiButton
            variant="text"
            icon
            size="sm"
            :loading="loading"
            :aria-label="t('common.refresh')"
            data-testid="report-readiness-refresh"
            @click="refresh()"
          >
            <RuiIcon
              name="lu-refresh-ccw"
              size="16"
            />
          </RuiButton>
        </div>
      </div>

      <FailureStrip
        v-if="actionFailure"
        :title="actionFailure.title"
        :failure="actionFailure.failure"
        data-testid="report-readiness-action-failure"
      />

      <ReportReadinessChecklist
        v-if="modelExpanded && openIssuesCount > 0"
        :groups="groupedIssues"
        :loading="issuesLoading"
        :busy="actionBusy"
        :error="issuesError"
        @action="runRemediation($event)"
        @retry="refresh()"
      />
    </div>

    <DataIssueRemediationModals
      v-model:price-update="modelPriceUpdate"
      v-model:event-form="modelEventForm"
      v-model:matching-open="modelMatchingOpen"
      v-model:sub-modal-open="modelSubModalOpen"
      @saved="onModalSaved()"
    />
  </section>
</template>
