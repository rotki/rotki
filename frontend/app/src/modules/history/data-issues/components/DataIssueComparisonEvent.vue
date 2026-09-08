<script setup lang="ts">
import type { DecodingEventDiff } from '@/modules/history/data-issues/decoding-comparison';
import type { DecodingComparisonEvent } from '@/modules/history/data-issues/schemas';
import ValueDisplay from '@/modules/assets/amount-display/components/ValueDisplay.vue';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DataIssueComparisonValue from '@/modules/history/data-issues/components/DataIssueComparisonValue.vue';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { diff, asset, sharedAccount, sharedTimestamp } = defineProps<{
  diff: DecodingEventDiff;
  asset: string;
  sharedAccount?: string;
  sharedTimestamp?: number;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getHistoryEventTypeName, getHistoryEventSubTypeName } = useHistoryEventMappings();
const event = computed<DecodingComparisonEvent | undefined>(() => diff.decoded ?? diff.saved);
const statusLabel = computed<string>(() => ({
  added: t('data_issues.detail.comparison.added'),
  removed: t('data_issues.detail.comparison.removed'),
  modified: t('data_issues.detail.comparison.modified'),
  unchanged: t('data_issues.detail.comparison.unchanged'),
})[diff.status]);
</script>

<template>
  <li
    v-if="event"
    class="border-l-2 p-3 text-body-2"
    :class="{
      'border-rui-error bg-rui-error/5': diff.status === 'removed',
      'border-rui-success bg-rui-success/5': diff.status === 'added',
      'border-rui-primary': diff.status === 'modified',
      'border-default text-rui-text-secondary': diff.status === 'unchanged',
    }"
    data-testid="data-issue-event-diff"
  >
    <div class="flex flex-wrap items-center gap-2">
      <span
        class="font-medium"
        data-testid="data-issue-diff-status"
      >
        {{ statusLabel }}
      </span>
      <span>{{ t('data_issues.detail.comparison.order', { index: event.sequenceIndex }) }}</span>
      <span v-if="!diff.fields.includes('eventType') && !diff.fields.includes('eventSubtype')">
        {{ getHistoryEventTypeName(event.eventType) }}
        <template v-if="event.eventSubtype && event.eventSubtype !== 'none'">
          / {{ getHistoryEventSubTypeName(event.eventSubtype) }}
        </template>
      </span>
      <template v-if="!diff.fields.includes('amount') && !diff.fields.includes('asset')">
        <ValueDisplay
          :value="event.amount"
          :format="{ decimals: event.amount.decimalPlaces() ?? undefined }"
        />
        <AssetDetails
          :asset="event.asset"
          :display="{ dense: true }"
        />
      </template>
      <RuiChip
        v-if="diff.saved?.customized"
        size="sm"
        color="warning"
      >
        {{ t('data_issues.detail.comparison.customized') }}
      </RuiChip>
    </div>
    <dl
      v-if="diff.status === 'modified' && diff.saved && diff.decoded"
      class="mt-2 flex flex-col gap-1"
    >
      <DataIssueComparisonValue
        v-for="field in diff.fields"
        :key="field"
        :field="field"
        :saved="diff.saved"
        :decoded="diff.decoded"
        :asset="asset"
      />
    </dl>
    <template v-else-if="diff.status !== 'unchanged'">
      <div class="flex flex-wrap items-center gap-2 mt-1">
        <DateDisplay
          v-if="event.timestamp !== sharedTimestamp"
          :timestamp="event.timestamp"
          milliseconds
        />
        <HistoryEventAccount
          v-if="event.locationLabel && event.locationLabel !== sharedAccount"
          :location="event.location"
          :location-label="event.locationLabel"
        />
        <HashLink
          v-if="event.address"
          :location="event.location"
          :text="event.address"
        />
      </div>
      <p
        v-if="event.userNotes"
        class="mt-1 break-words"
        data-testid="data-issue-diff-notes"
      >
        {{ event.userNotes }}
      </p>
      <div
        v-if="!event.balanceEffect.isZero()"
        class="mt-1 flex flex-wrap items-center gap-2"
        data-testid="data-issue-diff-effect"
      >
        {{ t('data_issues.detail.comparison.balance_effect') }}
        <ValueDisplay
          :value="event.balanceEffect"
          :format="{ decimals: event.balanceEffect.decimalPlaces() ?? undefined }"
        />
        <AssetDetails
          :asset="asset"
          :display="{ dense: true }"
        />
      </div>
    </template>
  </li>
</template>
