<script lang="ts" setup>
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItem from '@/components/history/events/HistoryEventsListItem.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';

const props = defineProps<{
  events: HistoryEventEntry[];
  highlightedIdentifiers?: string[];
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const isInitialRender = ref<boolean>(true);
const expanded = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const { getChain } = useSupportedChains();
const { getAssetSymbol } = useAssetInfoRetrieval();

const usedEvents = computed(() => {
  if (get(expanded)) {
    return props.events;
  }

  const filtered = props.events.filter(item => item.eventSubtype !== 'fee');

  // Separate the spend and receive events
  const spendEvents = filtered.filter(item => item.eventSubtype === 'spend');
  const receiveEvents = filtered.filter(item => item.eventSubtype === 'receive');

  // Create an alternating pattern
  const alternating: HistoryEventEntry[] = [];
  const maxPairs = Math.min(spendEvents.length, receiveEvents.length);

  for (let i = 0; i < maxPairs; i++) {
    if (spendEvents[i]) {
      alternating.push(spendEvents[i]);
    }
    if (receiveEvents[i]) {
      alternating.push(receiveEvents[i]);
    }
  }

  // Add remaining spend events if any
  if (spendEvents.length > receiveEvents.length) {
    const remainingSpend = spendEvents.slice(receiveEvents.length);
    alternating.push(...remainingSpend);
  }

  return alternating;
});

function getCompactNotes(events: HistoryEventEntry[]): string | undefined {
  const spend = events.filter(item => item.eventSubtype === 'spend');
  const receive = events.filter(item => item.eventSubtype === 'receive');

  if (spend.length === 0 || receive.length === 0) {
    return undefined;
  }

  const receiveNotes = receive.length === 1
    ? {
        receiveAmount: receive[0].amount,
        receiveAsset: getAssetSymbol(receive[0].asset),
      }
    : {
        receiveAmount: receive.length,
        receiveAsset: 'asset',
      };

  const spendNotes = spend.length === 1
    ? {
        spendAmount: spend[0].amount,
        spendAsset: getAssetSymbol(spend[0].asset),
      }
    : {
        spendAmount: spend.length,
        spendAsset: 'asset',
      };

  let notes = t('history_events_list_swap.swap_description', {
    ...receiveNotes,
    ...spendNotes,
  });

  const fee = props.events.filter(item => item.eventSubtype === 'fee');
  if (fee.length > 0) {
    const feeText = fee.map(item => `${item.amount} ${getAssetSymbol(item.asset)}`).join('; ');
    notes = t('history_events_list_swap.fee_description', {
      feeText,
      notes,
    });
  }

  return notes;
}

watch(expanded, () => {
  if (!get(isInitialRender)) {
    return;
  }
  set(isInitialRender, false);
});
</script>

<template>
  <TransitionGroup
    tag="div"
    name="list"
    class="relative group"
    :class="{
      'grid grid-cols-10 gap-x-2 gap-y-1 @5xl:!grid-cols-[repeat(20,minmax(0,1fr))] items-start @5xl:min-h-[80px]': !expanded,
      'flex flex-col': expanded,
      'transition-wrapper': !isInitialRender,
      'md:pl-3': !expanded,
    }"
  >
    <LazyLoader
      v-if="!expanded"
      key="history-event-type"
      class="col-span-10 md:col-span-4 @5xl:!col-span-5 py-4 lg:py-4.5 relative"
    >
      <RuiButton
        size="sm"
        icon
        color="primary"
        class="absolute top-2.5 -left-1 size-5 z-[6]"
        @click="expanded = !expanded"
      >
        <RuiIcon
          class="hidden group-hover:block"
          name="lu-unfold-vertical"
          size="14"
        />
        <span class="group-hover:hidden">{{ events.length }}</span>
      </RuiButton>
      <HistoryEventType
        icon="lu-arrow-right-left"
        :event="events[0]"
        highlight
        :chain="getChain(events[0].location)"
      />
    </LazyLoader>

    <div
      key="history-event-assets"
      class="flex flex-col col-span-10 md:col-span-6 @5xl:!col-span-8 relative"
      :class="{
        'md:py-2 grid grid-cols-10': !expanded,
      }"
    >
      <RuiButton
        v-if="expanded"
        size="sm"
        icon
        color="primary"
        class="absolute top-3 -left-2 md:left-1.5 size-5 z-[6]"
        @click="expanded = !expanded"
      >
        <RuiIcon
          class="hidden group-hover:block"
          name="lu-fold-vertical"
          size="14"
        />
        <span class="group-hover:hidden">{{ events.length }}</span>
      </RuiButton>
      <template
        v-for="(event, eventIndex) in usedEvents"
        :key="event.identifier"
      >
        <HistoryEventsListItem
          :class="{
            'col-start-1 col-span-4': !expanded && event.eventSubtype === 'spend',
            'col-start-6 col-span-5': !expanded && event.eventSubtype === 'receive',
          }"
          :item="event"
          :index="eventIndex"
          :data-subtype="event.eventSubtype"
          :events="usedEvents"
          :compact="!expanded"
          :event-group="events[0]"
          :is-last="eventIndex === events.length - 1"
          :is-highlighted="highlightedIdentifiers?.includes(event.identifier.toString())"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @show:missing-rule-action="emit('show:missing-rule-action', $event)"
        />

        <LazyLoader
          v-if="!expanded && eventIndex === 0 && usedEvents.length > 0"
          key="swap-arrow"
          class="flex items-center px-2 @md:pl-0 h-14 col-start-5"
        >
          <RuiIcon
            class="text-rui-grey-400 dark:text-rui-grey-600"
            name="lu-chevron-right"
            size="24"
          />
        </LazyLoader>
      </template>
    </div>

    <LazyLoader
      v-if="!expanded && getCompactNotes(events)"
      key="history-event-notes"
      class="py-2 pt-4 md:pl-0 @5xl:!pl-0 @5xl:pt-4 col-span-10 @md:col-span-7 @5xl:!col-span-4"
      min-height="80"
    >
      <HistoryEventNote
        :notes="getCompactNotes(events)"
        :amount="events.map(item => item.amount)"
      />
    </LazyLoader>

    <LazyLoader
      v-if="!expanded"
      key="history-event-actions"
      class="py-2 @5xl:!py-4 col-span-10 @md:col-span-3"
      min-height="40"
    >
      <HistoryEventsListItemAction
        :item="events[0]"
        :index="0"
        :events="events"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      />
    </LazyLoader>
  </TransitionGroup>
</template>

<style lang="scss" scoped>
.transition-wrapper {
  .list-move,
  .list-enter-active,
  .list-leave-active {
    @apply transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)];
  }

  .list-enter-from,
  .list-leave-to {
    @apply opacity-0;
  }

  .list-leave-active {
    @apply absolute w-full;

    &[data-subtype="fee"] {
      @apply transition-none !important;
    }
  }
}
</style>
