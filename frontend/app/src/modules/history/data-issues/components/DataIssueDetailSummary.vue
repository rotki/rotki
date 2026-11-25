<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { IssueDescription } from '@/modules/history/data-issues/types';
import type { RemediationRequest } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { type RouteLocationRaw, useRouter } from 'vue-router';
import DataIssueBalanceMismatchSummary from '@/modules/history/data-issues/components/DataIssueBalanceMismatchSummary.vue';
import DataIssueDescription from '@/modules/history/data-issues/components/DataIssueDescription.vue';
import DataIssueInlineActions from '@/modules/history/data-issues/components/DataIssueInlineActions.vue';
import DataIssueNegativeBalanceSummary from '@/modules/history/data-issues/components/DataIssueNegativeBalanceSummary.vue';
import { IssueKind } from '@/modules/history/data-issues/constants';
import { describeIssue, type NegativeBalanceValues, negativeBalanceValues, relatedEventRoute } from '@/modules/history/data-issues/transforms';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { busy = false, issue } = defineProps<{
  issue: DataIssue;
  busy?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  remediate: [request: RemediationRequest];
}>();

type Amount = IssueDescription['amounts'][string];

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const description = computed<IssueDescription>(() => describeIssue(issue));
const negativeBalance = computed<NegativeBalanceValues | undefined>(() => negativeBalanceValues(issue));

/** Balance mismatches and negative balances show their amounts as values; every other kind keeps its sentence. */
const mismatch = computed<{ derived: Amount; observed: Amount; delta: Amount } | undefined>(() => {
  const amounts = get(description).amounts;
  if (issue.kind !== IssueKind.CURRENT_BALANCE_MISMATCH || !amounts.derived || !amounts.observed || !amounts.delta)
    return undefined;
  return { delta: amounts.delta, derived: amounts.derived, observed: amounts.observed };
});

/** Deep-link to the offending history event (shared with the inbox panel). */
const relatedEventLink = computed<RouteLocationRaw | undefined>(() =>
  relatedEventRoute(issue.kind, get(description).eventIdentifier, issue.groupIdentifier, issue.asset));

/** Unmatched bridge and exchange-transfer links open the matching dialog, so they say what they will do. */
const relatedEventLabel = computed<string>(() => {
  if (issue.kind === IssueKind.UNMATCHED_BRIDGE || issue.kind === IssueKind.UNMATCHED_EXCHANGE_TRANSFER)
    return t('data_issues.detail.match_in_history');
  return t('data_issues.detail.open_event', { id: get(description).eventIdentifier ?? '' });
});

async function goToRelatedEvent(): Promise<void> {
  const link = get(relatedEventLink);
  if (!link)
    return;
  emit('close');
  await router.push(link);
}
</script>

<template>
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
      v-else
      :description="description"
      tag="p"
      class="text-sm text-rui-text"
    />
    <DataIssueInlineActions
      :issue="issue"
      :busy="busy"
      class="mt-1"
      @action="emit('remediate', $event)"
    />
    <div
      v-if="description.eventIdentifier !== undefined"
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
</template>
