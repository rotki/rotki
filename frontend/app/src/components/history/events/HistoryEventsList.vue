<script setup lang="ts" generic="">
import type { HistoryEventEntry } from '@/types/history/events';
import HistoryEventsListTable from '@/components/history/events/HistoryEventsListTable.vue';

interface DeleteData {
  canDelete: boolean;
  item: HistoryEventEntry;
}

interface EditData<T extends HistoryEventEntry = HistoryEventEntry> {
  event: T;
  eventsInGroup: T[];
}

const props = withDefaults(defineProps<{
  eventGroup: HistoryEventEntry;
  allEvents: HistoryEventEntry[];
  hasIgnoredEvent?: boolean;
  loading?: boolean;
  highlightedIdentifiers?: string[];
}>(), {
  loading: false,
});

const emit = defineEmits<{
  'edit-event': [data: EditData];
  'delete-event': [data: DeleteData];
  'show:missing-rule-action': [data: EditData];
}>();

const PER_BATCH = 6;
const currentLimit = ref<number>(PER_BATCH);
const { t } = useI18n();
const { allEvents, eventGroup } = toRefs(props);

const events = computed<HistoryEventEntry[]>(() => {
  const all = get(allEvents);
  const eventHeader = get(eventGroup);
  if (all.length === 0)
    return [eventHeader];

  return all
    .filter(({ hidden }) => !hidden)
    .sort((a, b) => Number(a.sequenceIndex) - Number(b.sequenceIndex));
});

const ignoredInAccounting = computed(() => get(eventGroup).ignoredInAccounting);

const showDropdown = computed(() => {
  const length = get(events).length;
  return (get(ignoredInAccounting) || length > PER_BATCH) && length > 0;
});

watch([eventGroup, ignoredInAccounting], ([current, currentIgnored], [old, oldIgnored]) => {
  if (current.eventIdentifier !== old.eventIdentifier || currentIgnored !== oldIgnored)
    set(currentLimit, currentIgnored ? 0 : PER_BATCH);
});

const limitedEvents = computed(() => {
  const limit = get(currentLimit);
  return limit === 0 ? [] : get(events).slice(0, limit);
});

const hasMoreEvents = computed(() => get(currentLimit) < get(events).length);

const containerRef = ref<HTMLElement | null>(null);

function scrollToTop() {
  get(containerRef)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function handleMoreClick() {
  const eventsLength = get(events).length;
  const oldLimit = get(currentLimit);
  if (oldLimit === 0) {
    set(currentLimit, PER_BATCH);
  }
  else if (oldLimit >= eventsLength) {
    set(currentLimit, 0);
    scrollToTop();
  }
  else {
    set(currentLimit, Math.min(oldLimit + PER_BATCH, eventsLength));
  }
}

const buttonText = computed(() => {
  const limit = get(currentLimit);
  const eventsLength = get(events).length;
  if (limit === 0)
    return t('transactions.events.view.show', { length: eventsLength });
  else if (!get(hasMoreEvents))
    return t('transactions.events.view.hide');
  else
    return t('transactions.events.view.load_more', { length: eventsLength - limit });
});
</script>

<template>
  <div
    ref="containerRef"
    :class="{ 'pl-[3.125rem]': hasIgnoredEvent }"
  >
    <HistoryEventsListTable
      :event-group="eventGroup"
      :events="limitedEvents"
      :total="events.length"
      :loading="loading"
      :highlighted-identifiers="highlightedIdentifiers"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', {
        event: $event,
        eventsInGroup: limitedEvents,
      })"
      @edit-event="emit('edit-event', {
        event: $event,
        eventsInGroup: limitedEvents,
      })"
    />
    <RuiButton
      v-if="showDropdown"
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
  </div>
</template>
