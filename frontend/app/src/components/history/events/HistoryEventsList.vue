<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { get, set } from '@vueuse/core';
import { flatten } from 'es-toolkit';
import { computed, ref, toRefs, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import ReportIssueDialog from '@/components/help/ReportIssueDialog.vue';
import HistoryEventsListTable from '@/components/history/events/HistoryEventsListTable.vue';
import { isSwapEvent } from '@/modules/history/management/forms/form-guards';

const props = withDefaults(defineProps<{
  eventGroup: HistoryEventEntry;
  allEvents: HistoryEventRow[];
  displayedEvents: HistoryEventRow[];
  hasIgnoredEvent?: boolean;
  loading?: boolean;
  hideActions?: boolean;
  highlightedIdentifiers?: string[];
  selection?: UseHistoryEventsSelectionModeReturn;
}>(), {
  loading: false,
});

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'refresh': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const PER_BATCH = 6;
const currentLimit = ref<number>(PER_BATCH);
const containerRef = ref<HTMLElement>();

const {
  allEvents,
  displayedEvents,
  eventGroup,
  hasIgnoredEvent,
  highlightedIdentifiers,
  loading,
} = toRefs(props);

function combineEvents(events: HistoryEventRow[], group: HistoryEventEntry): HistoryEventRow[] {
  if (events.length === 0) {
    return [group];
  }

  if (isSwapEvent(group)) {
    const allFlattened = flatten(events);
    if (allFlattened.length === 1 && Array.isArray(allFlattened[0])) {
      return [allFlattened[0]];
    }
    return [allFlattened];
  }

  return events.map((item) => {
    if (Array.isArray(item) && item.length === 1) {
      return item[0];
    }
    return item;
  });
}

const combinedDisplayedEvents = computed<HistoryEventRow[]>(() =>
  combineEvents(get(displayedEvents), get(eventGroup)),
);

const combinedAllEvents = computed<HistoryEventRow[]>(() =>
  combineEvents(get(allEvents), get(eventGroup)),
);

const limitedEvents = computed<HistoryEventRow[]>(() => {
  const limit = get(currentLimit);
  const arr = get(combinedDisplayedEvents);
  return arr.slice(0, limit);
});

const totalBlocks = computed<number>(() => get(combinedDisplayedEvents).length);

const hasMoreEvents = computed<boolean>(() => get(limitedEvents).length < get(totalBlocks));

const buttonText = computed<string>(() => {
  const shownCount = get(limitedEvents).length;
  const total = get(totalBlocks);

  if (shownCount === 0) {
    return t('transactions.events.view.show', { length: total });
  }
  if (shownCount >= total) {
    return t('transactions.events.view.hide');
  }
  const remain = total - shownCount;
  return t('transactions.events.view.load_more', { length: remain });
});

function handleMoreClick() {
  const limit = get(currentLimit);

  // If none currently shown, show up to PER_BATCH blocks
  if (limit === 0) {
    set(currentLimit, PER_BATCH);
    return;
  }

  // If all are shown, hide them by setting the limit to 0
  if (!get(hasMoreEvents)) {
    set(currentLimit, 0);
    scrollToTop();
    return;
  }

  // Otherwise, add PER_BATCH more
  const nextLimit = limit + PER_BATCH;
  set(currentLimit, Math.min(nextLimit, get(totalBlocks)));
}

function scrollToTop() {
  get(containerRef)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

watch(() => get(eventGroup), () => {
  set(currentLimit, PER_BATCH);
});

// Unsupported event detection
const unsupportedEvent = computed<HistoryEventEntry | null>(() => {
  const events = get(combinedAllEvents);
  if (events.length !== 1)
    return null;

  const event = events[0];
  if (Array.isArray(event))
    return null;

  const isGasFeeOnly = event.eventType === 'spend'
    && event.eventSubtype === 'fee'
    && 'counterparty' in event
    && event.counterparty === 'gas'
    && 'txRef' in event
    && event.txRef;

  return isGasFeeOnly ? event : null;
});

const showReportDialog = ref<boolean>(false);

const reportTitle = computed<string>(() => t('transactions.events.unsupported.report_title'));

const reportDescription = computed<string>(() => {
  const event = get(unsupportedEvent);
  if (!event)
    return '';

  const txRef = 'txRef' in event ? event.txRef : '';

  return [
    t('transactions.events.unsupported.report_description_intro'),
    txRef ? t('transactions.events.unsupported.tx_hash', { hash: txRef }) : '',
    t('transactions.events.unsupported.location', { location: event.location }),
    '',
    t('transactions.events.unsupported.more_detail'),
    t('transactions.events.unsupported.placeholder'),
  ].filter(Boolean).join('\n');
});
</script>

<template>
  <div
    ref="containerRef"
    :class="{ 'pl-[3.125rem]': hasIgnoredEvent }"
  >
    <div
      v-if="unsupportedEvent"
      class="flex items-center gap-2 px-2 py-1.5 mt-3 md:mx-3 bg-rui-warning-lighter/20 rounded"
    >
      <RuiIcon
        name="lu-circle-alert"
        class="text-rui-warning shrink-0"
        size="16"
      />
      <div class="flex-1 min-w-0">
        <span class="text-xs font-medium">{{ t('transactions.events.unsupported.title') }}</span>
        <span class="text-xs text-rui-text-secondary"> - {{ t('transactions.events.unsupported.description') }}</span>
      </div>
      <RuiButton
        color="warning"
        variant="text"
        size="sm"
        class="!py-0 !px-1 shrink-0"
        @click="showReportDialog = true"
      >
        {{ t('transactions.events.unsupported.report_action') }}
      </RuiButton>
    </div>

    <HistoryEventsListTable
      :key="eventGroup.groupIdentifier"
      :event-group="eventGroup"
      :events="limitedEvents"
      :all-events="combinedAllEvents"
      :total="totalBlocks"
      :loading="loading"
      :hide-actions="hideActions"
      :highlighted-identifiers="highlightedIdentifiers"
      :selection="selection"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      @edit-event="emit('edit-event', $event)"
      @refresh="emit('refresh')"
    />

    <RuiButton
      v-if="hasMoreEvents || currentLimit === 0"
      color="primary"
      variant="text"
      class="text-rui-primary font-bold my-2"
      @click="handleMoreClick()"
    >
      {{ buttonText }}
      <template #append>
        <RuiIcon
          class="transition-all"
          name="lu-chevron-down"
          :class="{ 'transform -rotate-180': !hasMoreEvents }"
        />
      </template>
    </RuiButton>

    <ReportIssueDialog
      v-model="showReportDialog"
      :initial-title="reportTitle"
      :initial-description="reportDescription"
    />
  </div>
</template>
