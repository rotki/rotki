<script setup lang="ts">
import type { DecodingComparisonEvent, TransactionDecodingComparison } from '@/modules/history/data-issues/schemas';
import DataIssueComparisonEvent from '@/modules/history/data-issues/components/DataIssueComparisonEvent.vue';
import { type DecodingEventDiff, diffDecodingEvents } from '@/modules/history/data-issues/decoding-comparison';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { transaction, asset } = defineProps<{
  transaction: TransactionDecodingComparison;
  asset: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const showUnchanged = ref<boolean>(false);
const diffs = computed<DecodingEventDiff[]>(() => diffDecodingEvents(transaction));
const unchanged = computed<number>(() => get(diffs).filter(diff => diff.status === 'unchanged').length);
const visible = computed<DecodingEventDiff[]>(() => get(diffs).filter(diff => get(showUnchanged) || diff.status !== 'unchanged'));
const events = computed<DecodingComparisonEvent[]>(() => [...transaction.savedEvents, ...transaction.decodedEvents]);
const sharedTimestamp = computed<number | undefined>(() => {
  const first = get(events)[0];
  return first && get(events).every(event => event.timestamp === first.timestamp) ? first.timestamp : undefined;
});
const sharedAccount = computed<string | undefined>(() => {
  const first = get(events)[0];
  return first?.locationLabel && get(events).every(event => event.locationLabel === first.locationLabel)
    ? first.locationLabel
    : undefined;
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex flex-wrap items-center gap-3 text-body-2 text-rui-text-secondary">
      <DateDisplay
        v-if="sharedTimestamp !== undefined"
        :timestamp="sharedTimestamp"
        milliseconds
      />
      <HistoryEventAccount
        v-if="sharedAccount"
        :location="transaction.savedEvents[0]?.location"
        :location-label="sharedAccount"
      />
    </div>
    <div
      v-if="visible.some(diff => diff.status === 'modified')"
      class="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_minmax(0,2fr)] gap-2 px-3 text-caption text-rui-text-secondary"
    >
      <span />
      <span>{{ t('data_issues.detail.comparison.before') }}</span>
      <span>{{ t('data_issues.detail.comparison.after') }}</span>
    </div>
    <ol
      class="flex flex-col gap-2"
      data-testid="data-issue-review-diffs"
    >
      <DataIssueComparisonEvent
        v-for="(diff, index) in visible"
        :key="index"
        :diff="diff"
        :asset="asset"
        :shared-account="sharedAccount"
        :shared-timestamp="sharedTimestamp"
      />
    </ol>
    <RuiButton
      v-if="unchanged"
      variant="text"
      size="sm"
      class="self-start"
      data-testid="data-issue-diff-toggle-unchanged"
      @click="showUnchanged = !showUnchanged"
    >
      {{ showUnchanged ? t('data_issues.detail.comparison.hide_unchanged', { count: unchanged }) : t('data_issues.detail.comparison.show_unchanged', { count: unchanged }) }}
    </RuiButton>
  </div>
</template>
