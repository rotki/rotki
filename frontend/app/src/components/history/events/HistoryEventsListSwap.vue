<script lang="ts" setup>
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
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

function getCompactNotes(events: HistoryEventEntry[]): string | undefined {
  const spend = events.find(item => item.eventSubtype === 'spend');
  const receive = events.find(item => item.eventSubtype === 'receive');

  if (!spend || !receive) {
    return undefined;
  }

  let notes = t('history_events_list_swap.swap_description', {
    receiveAmount: receive.amount,
    receiveAsset: getAssetSymbol(receive.asset),
    spendAmount: spend.amount,
    spendAsset: getAssetSymbol(spend.asset),
  });

  const fee = props.events.find(item => item.eventSubtype === 'fee');
  if (fee) {
    notes = t('history_events_list_swap.fee_description', {
      feeAmount: fee.amount,
      feeAsset: getAssetSymbol(fee.asset),
      notes,
    });
  }

  return notes;
}

function showArrow(event: HistoryEventEntry, index: number): boolean {
  const isSpend = event.eventSubtype === 'spend';
  const willBeReceive = props.events[index + 1]?.eventSubtype === 'receive';
  return isSpend && willBeReceive;
}

watch(expanded, () => {
  if (get(isInitialRender)) {
    set(isInitialRender, false);
  }
});
</script>

<template>
  <TransitionGroup
    tag="div"
    name="list"
    class="relative"
    :style="{ height: expanded ? 'auto' : '90px' }"
    :class="{
      'transition-wrapper': !isInitialRender,
    }"
  >
    <LazyLoader
      v-if="!expanded"
      class="pt-4 pb-0 lg:py-4.5 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 items-start gap-3 gap-y-1 py-3 px-0 md:px-3"
    >
      <HistoryEventType
        icon="lu-arrow-right-left"
        :event="events[0]"
        highlight
        :chain="getChain(events[0].location)"
      />

      <div
        v-for="(event, eventIndex) in events.filter(item => item.eventSubtype !== 'fee')"
        :key="event.identifier"
        class="flex flex-col md:flex-row"
      >
        <HistoryEventAsset
          :event="event"
          class="transition-all duration-300 w-full"
        />

        <div class="flex items-center">
          <RuiIcon
            v-if="showArrow(event, eventIndex)"
            class="text-rui-grey-400 dark:text-rui-grey-600 rotate-90 md:rotate-0"
            name="lu-chevron-right"
            size="24"
          />
        </div>
      </div>

      <HistoryEventNote
        v-if="getCompactNotes(events)"
        class="md:col-span-2 lg:col-span-1"
        :notes="getCompactNotes(events)"
        :amount="events.map(item => item.amount)"
      />

      <HistoryEventsListItemAction
        :item="events[0]"
        :index="0"
        :events="events"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      />
    </LazyLoader>
    <template v-else>
      <HistoryEventsListItem
        v-for="(event, index) in events"
        :key="event.identifier"
        class="flex-1"
        :item="event"
        :index="index"
        :events="events"
        :event-group="events[0]"
        :is-last="index === events.length - 1"
        :is-highlighted="highlightedIdentifiers?.includes(event.identifier.toString())"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      />
    </template>
  </TransitionGroup>
  <LazyLoader
    class="pb-2"
    min-height="36"
  >
    <RuiButton
      variant="text"
      color="primary"
      @click="expanded = !expanded"
    >
      <template #prepend>
        <RuiIcon
          name="lu-chevron-down"
          size="16"
          class="transition-all"
          :class="{ 'rotate-180': expanded }"
        />
      </template>
      {{ !expanded ? t('transactions.events.view.view_detail') : t('transactions.events.view.compact_view') }}
    </RuiButton>
  </LazyLoader>
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
