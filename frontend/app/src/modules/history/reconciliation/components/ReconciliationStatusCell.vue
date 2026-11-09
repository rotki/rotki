<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { MessageKey } from '@/message-key';
import type { ReconciliationBucket } from '@/modules/history/reconciliation/schemas';
import { reasonLabel, STATUS_LABEL } from '@/modules/history/reconciliation/messages';
import {
  amountsFor,
  type BucketAmounts,
  displayStatus,
  type DisplayStatus,
  displayStatusColor,
  displayStatusIcon,
  isHistoryFree,
  needsAttention,
} from '@/modules/history/reconciliation/use-reconciliation-rows';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { bucket } = defineProps<{
  bucket: ReconciliationBucket;
}>();

const emit = defineEmits<{
  'mark-spam': [bucket: ReconciliationBucket];
  'open-issue': [issueId: number];
}>();

const { t } = useI18n({ useScope: 'global' });

const status = computed<DisplayStatus>(() => displayStatus(bucket.status));
const amounts = computed<BucketAmounts>(() => amountsFor(bucket));
const attention = computed<boolean>(() => needsAttention(bucket.status));

const statusLabel = computed<string>(() => t(STATUS_LABEL[get(status)]));
const statusIcon = computed<string>(() => displayStatusIcon(get(status)));
const statusColor = computed<string>(() => displayStatusColor(get(status)));

const explanationKey = computed<MessageKey>(() => reasonLabel(bucket));

const comparedAt = computed<number | null>(() => get(amounts).comparedAt);
const observedAt = computed<number | null>(() => get(amounts).observedAt);

/** The event route is kept even when the issue link is missing or dismissed. */
const eventRoute = computed<RouteLocationRaw | undefined>(() => {
  const { stop } = bucket;
  if (stop === null)
    return undefined;

  const query: Record<string, string> = {
    highlightedNegativeBalanceEvent: String(stop.eventIdentifier),
    asset: bucket.asset,
  };
  if (stop.groupIdentifier)
    query.targetGroupIdentifier = stop.groupIdentifier;

  return { name: '/history/events/', query };
});

/**
 * Whether the spam action is offered.
 *
 * @remarks
 * Only a token held with no events at all is a spam candidate, and only when it is not a protocol
 * position. A native coin with missing history is a history problem, not spam.
 */
const canMarkSpam = computed<boolean>(() => {
  if (!isHistoryFree(bucket) || bucket.protocol !== null)
    return false;

  const identifier = bucket.asset.toLowerCase();
  return identifier.includes('/erc20:') || identifier.includes('/erc721:') || identifier.includes('/erc1155:');
});

function openIssue(): void {
  if (bucket.issueId !== null)
    emit('open-issue', bucket.issueId);
}
</script>

<template>
  <div
    class="flex flex-col gap-1"
    data-testid="reconciliation-status-cell"
  >
    <div
      class="flex items-center gap-1.5 font-medium"
      :class="statusColor"
    >
      <RuiIcon
        :name="statusIcon"
        size="16"
      />
      <span>{{ statusLabel }}</span>
    </div>

    <p class="text-xs text-rui-text-secondary !m-0 max-w-md">
      <i18n-t
        v-if="bucket.status === 'blocked' && bucket.stop"
        keypath="data_issues.reconciliation.reason.blocked"
        scope="global"
        tag="span"
      >
        <template #date>
          <DateDisplay
            :timestamp="bucket.stop.eventTimestamp"
            milliseconds
          />
        </template>
      </i18n-t>
      <span v-else>{{ t(explanationKey) }}</span>
    </p>

    <div
      v-if="comparedAt !== null"
      class="text-xs text-rui-text-disabled"
    >
      <i18n-t
        keypath="data_issues.reconciliation.compared_at"
        scope="global"
        tag="span"
      >
        <template #time>
          <TimeAgoDisplay :timestamp="comparedAt" />
        </template>
      </i18n-t>
    </div>
    <div
      v-if="observedAt !== null"
      class="text-xs text-rui-text-disabled"
    >
      <i18n-t
        keypath="data_issues.reconciliation.observed_at"
        scope="global"
        tag="span"
      >
        <template #time>
          <TimeAgoDisplay :timestamp="observedAt" />
        </template>
      </i18n-t>
    </div>

    <div
      v-if="attention || canMarkSpam"
      class="flex flex-wrap items-center gap-2 mt-0.5"
    >
      <RuiButton
        v-if="bucket.issueId !== null"
        size="sm"
        variant="text"
        color="primary"
        data-testid="reconciliation-open-issue"
        @click="openIssue()"
      >
        {{ t('data_issues.reconciliation.action.open_issue') }}
      </RuiButton>
      <RuiButton
        v-if="canMarkSpam"
        size="sm"
        variant="text"
        color="error"
        data-testid="reconciliation-mark-spam"
        @click="emit('mark-spam', bucket)"
      >
        {{ t('data_issues.reconciliation.action.mark_spam') }}
      </RuiButton>
      <RouterLink
        v-if="eventRoute"
        :to="eventRoute"
        class="text-sm text-rui-primary hover:underline"
        data-testid="reconciliation-view-event"
      >
        {{ t('data_issues.reconciliation.action.view_event') }}
      </RouterLink>
      <span
        v-if="bucket.status === 'mismatch' && bucket.issueId === null"
        class="text-xs text-rui-text-secondary"
        data-testid="reconciliation-mismatch-hint"
      >
        {{ t('data_issues.reconciliation.action.sync_hint') }}
      </span>
    </div>
  </div>
</template>
