<script setup lang="ts">
import type { ComparisonField } from '@/modules/history/data-issues/decoding-comparison';
import type { DecodingComparisonEvent } from '@/modules/history/data-issues/schemas';
import ValueDisplay from '@/modules/assets/amount-display/components/ValueDisplay.vue';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { field, saved, decoded, asset } = defineProps<{
  field: ComparisonField;
  saved: DecodingComparisonEvent;
  decoded: DecodingComparisonEvent;
  asset: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getHistoryEventTypeName, getHistoryEventSubTypeName } = useHistoryEventMappings();
const label = computed<string>(() => ({
  amount: t('common.amount'),
  asset: t('common.asset'),
  balanceEffect: t('data_issues.detail.comparison.balance_effect'),
  sequenceIndex: t('data_issues.detail.comparison.event_order'),
  timestamp: t('data_issues.detail.event_date'),
  location: t('common.location'),
  locationLabel: t('common.account'),
  counterparty: t('data_issues.detail.comparison.counterparty'),
  address: t('data_issues.detail.comparison.address'),
  userNotes: t('data_issues.detail.comparison.notes'),
  eventType: t('data_issues.detail.comparison.event_type'),
  eventSubtype: t('data_issues.detail.comparison.event_subtype'),
})[field]);

function textValue(event: DecodingComparisonEvent): string {
  if (field === 'eventType')
    return getHistoryEventTypeName(event.eventType);
  if (field === 'eventSubtype')
    return getHistoryEventSubTypeName(event.eventSubtype || 'none');
  return event[field]?.toString() || t('data_issues.detail.comparison.empty');
}
</script>

<template>
  <div
    class="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_minmax(0,2fr)] gap-2 items-start"
    data-testid="data-issue-diff-field"
  >
    <dt class="text-rui-text-secondary py-1">
      {{ label }}
    </dt>
    <dd
      v-for="(event, index) in [saved, decoded]"
      :key="index"
      class="rounded px-2 py-1 min-w-0 break-words"
      :class="index === 0 ? 'bg-rui-error/10' : 'bg-rui-success/10'"
      :data-testid="index === 0 ? 'data-issue-diff-before' : 'data-issue-diff-after'"
    >
      <span class="sr-only">{{ index === 0 ? t('data_issues.detail.comparison.before') : t('data_issues.detail.comparison.after') }}</span>
      <template v-if="field === 'amount' || field === 'balanceEffect'">
        <ValueDisplay
          :value="event[field]"
          :format="{ decimals: event[field].decimalPlaces() ?? undefined }"
        />
        <AssetDetails
          :asset="field === 'amount' ? event.asset : asset"
          :display="{ dense: true }"
        />
      </template>
      <AssetDetails
        v-else-if="field === 'asset'"
        :asset="event.asset"
        :display="{ dense: true }"
      />
      <DateDisplay
        v-else-if="field === 'timestamp'"
        :timestamp="event.timestamp"
        milliseconds
      />
      <template v-else>
        {{ textValue(event) }}
      </template>
    </dd>
  </div>
</template>
