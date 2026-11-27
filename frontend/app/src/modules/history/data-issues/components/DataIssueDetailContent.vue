<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { IssueDescription, RemediationTimelineItem } from '@/modules/history/data-issues/types';
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { type RouteLocationRaw, useRouter } from 'vue-router';
import DataIssueBalanceDivergence from '@/modules/history/data-issues/components/DataIssueBalanceDivergence.vue';
import DataIssueBalanceMismatchSummary from '@/modules/history/data-issues/components/DataIssueBalanceMismatchSummary.vue';
import DataIssueDescription from '@/modules/history/data-issues/components/DataIssueDescription.vue';
import DataIssueDetailFooter from '@/modules/history/data-issues/components/DataIssueDetailFooter.vue';
import DataIssueDetailHeader from '@/modules/history/data-issues/components/DataIssueDetailHeader.vue';
import DataIssueNegativeBalanceSummary from '@/modules/history/data-issues/components/DataIssueNegativeBalanceSummary.vue';
import DataIssueRemediationTimeline from '@/modules/history/data-issues/components/DataIssueRemediationTimeline.vue';
import { IssueKind } from '@/modules/history/data-issues/constants';
import { describeIssue, type NegativeBalanceValues, negativeBalanceValues, relatedEventRoute, toTimelineItems } from '@/modules/history/data-issues/transforms';
import { dataIssueDivergenceKey } from '@/modules/history/data-issues/use-data-issue-divergence-store';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

/**
 * One issue's detail body, shared by both of its containers: the drawer on the data-issues page and
 * the bottom sheet in the pinned rail. Owns no open state, emitting `close` for each to interpret.
 */
const { issue, busy = false, failure, spamAssessment } = defineProps<{
  issue?: DataIssue;
  busy?: boolean;
  /** The last failed dismiss or retry on the issue shown, passed on to the footer that names it. */
  failure?: InstanceType<typeof DataIssueDetailFooter>['$props']['failure'];
  /** Local spam model estimate for the issue's ERC-20 asset, forwarded to the header subject bar. */
  spamAssessment?: InstanceType<typeof DataIssueDetailHeader>['$props']['spamAssessment'];
}>();

const emit = defineEmits<{
  close: [];
  dismiss: [id: number];
  retry: [id: number];
  resolve: [id: number];
  review: [item: RemediationTimelineItem];
}>();

type Amount = IssueDescription['amounts'][string];

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const description = computed<IssueDescription | undefined>(() => issue ? describeIssue(issue) : undefined);

const negativeBalance = computed<NegativeBalanceValues | undefined>(() => issue ? negativeBalanceValues(issue) : undefined);

/** Balance mismatches and negative balances show their amounts as values; every other kind keeps its sentence. */
const mismatch = computed<{ derived: Amount; observed: Amount; delta: Amount } | undefined>(() => {
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
    <DataIssueDetailHeader
      :issue="issue"
      :spam-assessment="spamAssessment"
      @close="emit('close')"
    />

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

    <DataIssueDetailFooter
      :issue="issue"
      :busy="busy"
      :failure="failure"
      @dismiss="emit('dismiss', $event)"
      @retry="emit('retry', $event)"
      @resolve="emit('resolve', $event)"
    />
  </div>
</template>
