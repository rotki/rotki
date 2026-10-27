<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { IssueDescription, RemediationTimelineItem } from '@/modules/history/data-issues/types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DataIssueBalanceDivergence from '@/modules/history/data-issues/components/DataIssueBalanceDivergence.vue';
import DataIssueBalanceMismatchSummary from '@/modules/history/data-issues/components/DataIssueBalanceMismatchSummary.vue';
import DataIssueDescription from '@/modules/history/data-issues/components/DataIssueDescription.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueNegativeBalanceSummary from '@/modules/history/data-issues/components/DataIssueNegativeBalanceSummary.vue';
import DataIssueRemediationTimeline from '@/modules/history/data-issues/components/DataIssueRemediationTimeline.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import { canDismiss, canResolveManually, canRetry, IssueKind, IssueState } from '@/modules/history/data-issues/constants';
import { describeIssue, type NegativeBalanceValues, negativeBalanceValues, relatedEventRoute, toTimelineItems } from '@/modules/history/data-issues/transforms';
import { dataIssueDivergenceKey } from '@/modules/history/data-issues/use-data-issue-divergence-store';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

/**
 * One issue's detail body, shared by both of its containers: the drawer on the data-issues page and
 * the bottom sheet in the pinned rail. Owns no open state, emitting `close` for each to interpret.
 */
const { issue, busy = false } = defineProps<{
  issue?: DataIssue;
  busy?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  dismiss: [id: number];
  retry: [id: number];
  resolve: [id: number];
  review: [item: RemediationTimelineItem];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const description = computed<IssueDescription | undefined>(() => issue ? describeIssue(issue) : undefined);

const negativeBalance = computed<NegativeBalanceValues | undefined>(() => issue ? negativeBalanceValues(issue) : undefined);

/** Balance mismatches and negative balances show their amounts as values; every other kind keeps its sentence. */
const mismatch = computed<{ derived: BigNumber; observed: BigNumber; delta: BigNumber } | undefined>(() => {
  const amounts = get(description)?.amounts;
  if (issue?.kind !== IssueKind.CURRENT_BALANCE_MISMATCH || !amounts?.derived || !amounts.observed || !amounts.delta)
    return undefined;
  return { delta: amounts.delta, derived: amounts.derived, observed: amounts.observed };
});

/** Deep-link to the offending history event (shared with the inbox panel). */
const relatedEventLink = computed<RouteLocationRaw | undefined>(() =>
  issue ? relatedEventRoute(issue.kind, get(description)?.eventIdentifier, issue.groupIdentifier, issue.asset) : undefined);

/** An unmatched bridge's link opens the matching dialog, so it says what it will do. */
const relatedEventLabel = computed<string>(() => {
  if (issue?.kind === IssueKind.UNMATCHED_BRIDGE)
    return t('data_issues.detail.match_in_history');
  return t('data_issues.detail.open_event', { id: get(description)?.eventIdentifier ?? '' });
});

async function goToRelatedEvent(): Promise<void> {
  const link = get(relatedEventLink);
  if (!link)
    return;
  emit('close');
  await router.push(link);
}

const timeline = computed<RemediationTimelineItem[]>(() => (issue ? toTimelineItems(issue) : []));

const resolutionNote = computed<string | undefined>(() => {
  const resolution = issue?.payload?.resolution;
  if (resolution && typeof resolution === 'object' && 'note' in resolution) {
    const note = resolution.note;
    return typeof note === 'string' ? note : undefined;
  }
  return undefined;
});
</script>

<template>
  <div
    v-if="issue"
    class="flex flex-col h-full"
  >
    <div class="flex flex-col gap-2 py-2 pl-4 pr-2 border-b border-rui-divider">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-base font-semibold text-rui-text">
          {{ t('data_issues.detail.title') }}
        </h2>
        <RuiButton
          variant="text"
          icon
          class="text-rui-text-secondary!"
          :aria-label="t('common.actions.close')"
          @click="emit('close')"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>
      <div class="flex flex-wrap items-center gap-2 text-xs text-rui-text-secondary">
        <DataIssueKindChip :kind="issue.kind" />
        <DataIssueStateChip :state="issue.state" />
        <span class="ml-1">
          {{ t('data_issues.detail.detected') }}
          <TimeAgoDisplay :timestamp="issue.createdAt" />
        </span>
      </div>
      <div
        class="flex flex-wrap items-center gap-x-5 gap-y-2 pb-2 text-sm"
        data-testid="data-issue-subject"
      >
        <span class="inline-flex items-center">
          <span class="sr-only">{{ t('common.account') }}</span>
          <HistoryEventAccount
            v-if="issue.locationLabel"
            :location="issue.location"
            :location-label="issue.locationLabel"
          />
          <span
            v-else
            class="text-rui-text-secondary"
          >
            -
          </span>
        </span>
        <span class="inline-flex items-center">
          <span class="sr-only">{{ t('common.location') }}</span>
          <LocationDisplay
            :identifier="issue.location"
            horizontal
            size="20px"
            class="w-fit"
          />
        </span>
        <span
          v-if="issue.asset"
          class="inline-flex items-center"
        >
          <span class="sr-only">{{ t('common.asset') }}</span>
          <AssetDetails
            :asset="issue.asset"
            :display="{ dense: true, inline: true, size: '20px' }"
          />
        </span>
        <span
          v-if="issue.protocol"
          class="inline-flex items-center"
        >
          <span class="sr-only">{{ t('common.protocol') }}</span>
          <CounterpartyDisplay :counterparty="issue.protocol" />
        </span>
      </div>
    </div>

    <div class="flex flex-col p-4 overflow-y-auto grow between:border-t between:border-rui-divider between:mt-4 between:pt-4">
      <section class="flex flex-col gap-2">
        <h3 class="text-xs font-medium text-rui-text-secondary">
          {{ t('data_issues.detail.whats_wrong') }}
        </h3>
        <DataIssueBalanceMismatchSummary
          v-if="mismatch"
          v-bind="mismatch"
          :asset="issue.asset ?? undefined"
        />
        <DataIssueNegativeBalanceSummary
          v-else-if="negativeBalance"
          v-bind="negativeBalance"
          :asset="issue.asset ?? undefined"
        />
        <DataIssueDescription
          v-else-if="description"
          :description="description"
          tag="p"
          class="text-sm text-rui-text"
        />
        <div
          v-if="description?.eventIdentifier !== undefined"
          class="mt-1 flex flex-wrap items-center justify-between gap-x-2 text-xs text-rui-text-secondary"
        >
          <span data-testid="data-issue-event-date">
            {{ t('data_issues.detail.event_date') }}
            <DateDisplay
              :timestamp="issue.tsEnd"
              milliseconds
            />
          </span>
          <RuiButton
            v-if="relatedEventLink"
            variant="text"
            color="primary"
            size="sm"
            class="-mr-2"
            data-testid="data-issue-related-event"
            @click="goToRelatedEvent()"
          >
            {{ relatedEventLabel }}
            <template #append>
              <RuiIcon
                name="lu-arrow-right"
                size="14"
              />
            </template>
          </RuiButton>
        </div>
      </section>

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

      <section
        v-if="resolutionNote"
        class="flex flex-col gap-2"
      >
        <h3 class="text-xs font-medium text-rui-text-secondary">
          {{ t('data_issues.detail.resolution_note') }}
        </h3>
        <p class="text-sm">
          {{ resolutionNote }}
        </p>
      </section>
    </div>

    <div class="flex items-center justify-end gap-2 p-4 border-t border-rui-divider">
      <RuiButton
        variant="outlined"
        :disabled="busy || !canDismiss(issue.state)"
        data-testid="data-issue-detail-dismiss"
        @click="emit('dismiss', issue.id)"
      >
        {{ t('data_issues.action.dismiss.label') }}
      </RuiButton>
      <RuiButton
        v-if="canRetry(issue.kind, issue.state) || issue.state === IssueState.AUTO_REMEDIATING"
        variant="outlined"
        color="primary"
        :disabled="busy || !canRetry(issue.kind, issue.state)"
        data-testid="data-issue-detail-retry"
        @click="emit('retry', issue.id)"
      >
        {{ t('data_issues.action.retry.label') }}
      </RuiButton>
      <RuiButton
        color="primary"
        :disabled="busy || !canResolveManually(issue.state)"
        data-testid="data-issue-detail-resolve"
        @click="emit('resolve', issue.id)"
      >
        {{ t('data_issues.action.resolve.label') }}
      </RuiButton>
    </div>
  </div>
</template>
