<script setup lang="ts">
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events';
import HistoryEventsListTable from '@/components/history/events/HistoryEventsListTable.vue';
import { isSwapEvent } from '@/modules/history/management/forms/form-guards';
import { get, set } from '@vueuse/core';
import { flatten } from 'es-toolkit';
import { computed, ref, toRefs, watch } from 'vue';
import { useI18n } from 'vue-i18n';

const props = withDefaults(defineProps<{
  eventGroup: HistoryEventEntry;
  allEvents: HistoryEventRow[];
  hasIgnoredEvent?: boolean;
  loading?: boolean;
  highlightedIdentifiers?: string[];
}>(), {
  loading: false,
});

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const { t } = useI18n();

const PER_BATCH = 6;
const currentLimit = ref<number>(PER_BATCH);
const containerRef = ref<HTMLElement>();

const {
  allEvents,
  eventGroup,
  hasIgnoredEvent,
  highlightedIdentifiers,
  loading,
} = toRefs(props);

const combinedAllEvents = computed<HistoryEventRow[]>(() => {
  const all = get(allEvents);
  const group = get(eventGroup);
  if (all.length === 0) {
    return [group];
  }

  if (isSwapEvent(group)) {
    return [flatten(all)];
  }
  return all;
});

const limitedEvents = computed<HistoryEventRow[]>(() => {
  const limit = get(currentLimit);
  const arr = get(combinedAllEvents);
  return arr.slice(0, limit);
});

const totalBlocks = computed<number>(() => get(combinedAllEvents).length);

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
</script>

<template>
  <div
    ref="containerRef"
    :class="{ 'pl-[3.125rem]': hasIgnoredEvent }"
  >
    <HistoryEventsListTable
      :key="eventGroup.eventIdentifier"
      :event-group="eventGroup"
      :events="limitedEvents"
      :total="totalBlocks"
      :loading="loading"
      :highlighted-identifiers="highlightedIdentifiers"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      @edit-event="emit('edit-event', $event)"
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
  </div>
</template>
