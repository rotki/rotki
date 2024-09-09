<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    eventGroup: HistoryEventEntry;
    allEvents: HistoryEventEntry[];
    hasIgnoredEvent?: boolean;
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'edit-event', data: HistoryEventEntry): void;
  (
    e: 'delete-event',
    data: {
      canDelete: boolean;
      item: HistoryEventEntry;
    },
  ): void;
  (e: 'show:missing-rule-action', data: HistoryEventEntry): void;
}>();

const PER_BATCH = 6;
const currentLimit = ref<number>(PER_BATCH);
const { t } = useI18n();
const { eventGroup, allEvents } = toRefs(props);

const events = computed<HistoryEventEntry[]>(() => {
  const all = get(allEvents);
  const eventHeader = get(eventGroup);
  if (all.length === 0)
    return [eventHeader];
  const eventIdentifierHeader = eventHeader.eventIdentifier;
  return all
    .filter(({ eventIdentifier, hidden }) => eventIdentifier === eventIdentifierHeader && !hidden)
    .sort((a, b) => Number(a.sequenceIndex) - Number(b.sequenceIndex));
});

const ignoredInAccounting = computed(() => !!get(eventGroup).ignoredInAccounting);

const showDropdown = computed(() => {
  const length = events.value.length;
  return (ignoredInAccounting.value || length > PER_BATCH) && length > 0;
});

watch([eventGroup, ignoredInAccounting], ([current, currentIgnored], [old, oldIgnored]) => {
  if (current.eventIdentifier !== old.eventIdentifier || currentIgnored !== oldIgnored)
    currentLimit.value = currentIgnored ? 0 : PER_BATCH;
});

const limitedEvents = computed(() => {
  const limit = currentLimit.value;
  return limit === 0 ? [] : events.value.slice(0, limit);
});

const hasMoreEvents = computed(() => currentLimit.value < events.value.length);

const containerRef = ref<HTMLElement | null>(null);

function scrollToTop() {
  containerRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function handleMoreClick() {
  const eventsLength = events.value.length;
  const oldLimit = currentLimit.value;
  if (oldLimit === 0) {
    currentLimit.value = PER_BATCH;
  }
  else if (oldLimit >= eventsLength) {
    currentLimit.value = 0;
    scrollToTop();
  }
  else {
    currentLimit.value = Math.min(oldLimit + PER_BATCH, eventsLength);
  }
}

const buttonText = computed(() => {
  if (currentLimit.value === 0)
    return t('transactions.events.view.show', { length: events.value.length });
  else if (!hasMoreEvents.value)
    return t('transactions.events.view.hide');
  else
    return t('transactions.events.view.load_more', { length: events.value.length - currentLimit.value });
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
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      @edit-event="emit('edit-event', $event)"
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
          name="arrow-down-s-line"
          :class="{ 'transform -rotate-180': !hasMoreEvents }"
        />
      </template>
    </RuiButton>
  </div>
</template>
