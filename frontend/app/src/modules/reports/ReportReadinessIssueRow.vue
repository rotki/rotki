<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { IssueDescription } from '@/modules/history/data-issues/types';
import type { RemediationRequest } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import { RuiButton } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DataIssueDescription from '@/modules/history/data-issues/components/DataIssueDescription.vue';
import DataIssueInlineActions from '@/modules/history/data-issues/components/DataIssueInlineActions.vue';
import { describeIssue, relatedEventRoute } from '@/modules/history/data-issues/transforms';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { busy = false, issue } = defineProps<{
  issue: DataIssue;
  busy?: boolean;
}>();

const emit = defineEmits<{
  action: [request: RemediationRequest];
}>();

const { t } = useI18n({ useScope: 'global' });

const description = computed<IssueDescription>(() => describeIssue(issue));
const eventRoute = computed<RouteLocationRaw | undefined>(() =>
  relatedEventRoute(issue.kind, get(description).eventIdentifier, issue.groupIdentifier, issue.asset),
);
const issueDetailRoute = computed<RouteLocationRaw>(() => ({
  name: '/history/data-issues/[[tab]]',
  params: { tab: 'issues' },
  query: { issue: issue.id.toString() },
}));
</script>

<template>
  <li
    class="flex flex-col gap-2 py-3 px-3 border-t border-rui-divider first:border-t-0"
    data-testid="report-readiness-issue-row"
    :data-issue-id="issue.id"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm min-w-0">
        <AssetDetails
          v-if="issue.asset"
          :asset="issue.asset"
          :display="{ dense: true, inline: true, size: '20px' }"
        />
        <HistoryEventAccount
          v-if="issue.locationLabel"
          :location="issue.location"
          :location-label="issue.locationLabel"
          dense
        />
        <LocationDisplay
          v-else
          :identifier="issue.location"
          horizontal
          size="18px"
        />
        <DateDisplay
          :timestamp="issue.tsEnd || issue.tsStart"
          milliseconds
          class="text-xs text-rui-text-secondary whitespace-nowrap"
        />
      </div>

      <div class="flex items-center gap-1 shrink-0">
        <RouterLink
          v-if="eventRoute"
          :to="eventRoute"
        >
          <RuiButton
            variant="text"
            size="xs"
            color="primary"
            data-testid="report-readiness-open-event"
          >
            {{ t('data_issues.panel.goto_event') }}
          </RuiButton>
        </RouterLink>
        <RouterLink :to="issueDetailRoute">
          <RuiButton
            variant="text"
            size="xs"
            data-testid="report-readiness-open-detail"
          >
            {{ t('data_issues.view_details') }}
          </RuiButton>
        </RouterLink>
      </div>
    </div>

    <DataIssueDescription
      :description="description"
      tag="p"
      short
      class="text-xs text-rui-text-secondary"
    />

    <DataIssueInlineActions
      :issue="issue"
      :busy="busy"
      compact
      @action="emit('action', $event)"
    />
  </li>
</template>
