<script lang="ts" setup>
import type { RuiIcons } from '@rotki/ui-library';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItem from '@/components/history/events/HistoryEventsListItem.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useSupportedChains } from '@/composables/info/chains';
import { isSwapTypeEvent } from '@/modules/history/management/forms/form-guards';

const props = defineProps<{
  events: HistoryEventEntry[];
  allEvents: HistoryEventEntry[];
  highlightedIdentifiers?: string[];
  selection?: UseHistoryEventsSelectionModeReturn;
  hideActions?: boolean;
  hideIgnoredAssets?: boolean;
  isLast: boolean;
  hasIgnoredAssets?: boolean;
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'unlink-event': [data: HistoryEventUnlinkPayload];
  'refresh': [];
}>();

const isInitialRender = ref<boolean>(true);
const expanded = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const { getChain } = useSupportedChains();
const { getAssetSymbol } = useAssetInfoRetrieval();
const { getEventTypeData } = useHistoryEventMappings();

// Force expansion when the group has hidden ignored assets (to prevent broken swap display)
const hasHiddenIgnoredAssets = computed<boolean>(() => !!props.hasIgnoredAssets && !!props.hideIgnoredAssets);

const shouldExpand = computed<boolean>(() => get(expanded) || !!(props.selection && get(props.selection.isSelectionMode)) || get(hasHiddenIgnoredAssets));

const isSwapGroup = computed<boolean>(() => props.events.length > 0 && isSwapTypeEvent(props.events[0].entryType));

const primaryEvent = computed<HistoryEventEntry>(() => {
  if (get(isSwapGroup))
    return props.events[0];

  // For asset movements, use the first non-fee asset movement event
  const assetMovementEvent = props.events.find(
    item => item.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT && item.eventSubtype !== 'fee',
  );
  return assetMovementEvent ?? props.events[0];
});

const canUnlink = computed<boolean>(() => !!get(primaryEvent).actualGroupIdentifier);

const subgroupIcon = computed<RuiIcons | undefined>(() => {
  if (get(isSwapGroup))
    return 'lu-arrow-right-left';

  return get(getEventTypeData(get(primaryEvent))).icon;
});

const usedEvents = computed<HistoryEventEntry[]>(() => {
  if (get(shouldExpand)) {
    return props.events;
  }

  // For non-swap groups (like asset movements), show only the primary event
  if (!get(isSwapGroup)) {
    return [get(primaryEvent)];
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
  else if (receiveEvents.length > spendEvents.length) {
    const remainingSpend = receiveEvents.slice(spendEvents.length);
    alternating.push(...remainingSpend);
  }

  return alternating;
});

function appendFeeNotes(notes: string | undefined): string | undefined {
  const fee = props.events.filter(item => item.eventSubtype === 'fee');
  if (fee.length === 0)
    return notes;

  const feeText = fee.map(item => `${item.amount} ${getAssetSymbol(item.asset, { collectionParent: false })}`).join('; ');
  return t('history_events_list_swap.fee_description', { feeText, notes });
}

const compactNotes = computed<string | undefined>(() => {
  // For non-swap groups (asset movements), build notes from primary and secondary events
  if (!get(isSwapGroup)) {
    const primary = get(primaryEvent);
    // Secondary event is the one that's NOT an asset movement event (e.g., EVM event)
    const secondary = props.events.find(
      item => item.entryType !== HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    );

    const options = { collectionParent: false };
    const amount = primary.amount;
    const asset = getAssetSymbol(primary.asset, options);
    const locationLabel = primary.locationLabel ?? '';
    const address = secondary?.locationLabel ?? '';

    const notes = primary.eventType === 'deposit'
      ? t('asset_movement_matching.compact_notes.deposit', { address, amount, asset, locationLabel })
      : t('asset_movement_matching.compact_notes.withdraw', { address, amount, asset, locationLabel });

    return appendFeeNotes(notes);
  }

  // Swap-specific compact notes
  const spend = props.events.filter(item => item.eventSubtype === 'spend');
  const receive = props.events.filter(item => item.eventSubtype === 'receive');

  if (spend.length === 0 || receive.length === 0)
    return undefined;

  const options = { collectionParent: false };

  const receiveNotes = receive.length === 1
    ? {
        receiveAmount: receive[0].amount,
        receiveAsset: getAssetSymbol(receive[0].asset, options),
      }
    : {
        receiveAmount: receive.length,
        receiveAsset: 'asset',
      };

  const spendNotes = spend.length === 1
    ? {
        spendAmount: spend[0].amount,
        spendAsset: getAssetSymbol(spend[0].asset, options),
      }
    : {
        spendAmount: spend.length,
        spendAsset: 'asset',
      };

  const notes = t('history_events_list_swap.swap_description', {
    ...receiveNotes,
    ...spendNotes,
  });

  return appendFeeNotes(notes);
});

watch(shouldExpand, () => {
  if (!get(isInitialRender)) {
    return;
  }
  set(isInitialRender, false);
});
</script>

<template>
  <div
    class="flex items-start border-default"
    :class="{
      'border-b': !isLast,
    }"
  >
    <TransitionGroup
      tag="div"
      name="list"
      class="relative group flex-1"
      :class="{
        'grid grid-cols-10 gap-x-2 gap-y-1 @5xl:!grid-cols-[repeat(20,minmax(0,1fr))] items-start @5xl:min-h-[80px]': !shouldExpand,
        'flex flex-col': shouldExpand,
        'transition-wrapper': !isInitialRender,
        'md:pl-3': !shouldExpand,
      }"
    >
      <LazyLoader
        v-if="!shouldExpand"
        key="history-event-type"
        class="col-span-10 md:col-span-4 @5xl:!col-span-5 py-4 lg:py-4.5 relative"
      >
        <RuiButton
          v-if="!selection?.isSelectionMode.value && !hasHiddenIgnoredAssets"
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
          :icon="subgroupIcon"
          :event="primaryEvent"
          highlight
          :chain="getChain(primaryEvent.location)"
          hide-customized-chip
        />
      </LazyLoader>

      <div
        key="history-event-assets"
        class="flex flex-col col-span-10 md:col-span-6 relative"
        :class="{
          'md:py-2 grid grid-cols-10': !shouldExpand,
          '@5xl:!col-span-8': isSwapGroup,
          '@5xl:!col-span-4': !isSwapGroup,
        }"
      >
        <RuiButton
          v-if="shouldExpand && !selection?.isSelectionMode.value && !hasHiddenIgnoredAssets"
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
              'col-start-1 col-span-4': !shouldExpand && event.eventSubtype === 'spend',
              'col-start-6 col-span-5': !shouldExpand && event.eventSubtype === 'receive',
            }"
            :item="event"
            :index="eventIndex"
            :data-subtype="event.eventSubtype"
            :events="allEvents"
            :compact="!shouldExpand"
            :event-group="events[0]"
            :hide-actions="hideActions"
            :is-last="eventIndex === events.length - 1"
            :is-highlighted="highlightedIdentifiers?.includes(event.identifier.toString())"
            :selection="selection"
            @edit-event="emit('edit-event', $event)"
            @delete-event="emit('delete-event', $event)"
            @show:missing-rule-action="emit('show:missing-rule-action', $event)"
            @unlink-event="emit('unlink-event', $event)"
            @refresh="emit('refresh')"
          />

          <LazyLoader
            v-if="!shouldExpand && eventIndex === 0 && usedEvents.length > 1"
            key="swap-arrow"
            class="flex items-center px-2 @md:pl-0 !h-14"
            :class="{
              'col-start-5': isSwapGroup,
              'col-start-4': !isSwapGroup,
            }"
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
        v-if="!shouldExpand"
        key="history-event-notes"
        class="py-2 pt-4 md:pl-0 @5xl:!pl-0 @5xl:pt-4 col-span-10 @md:col-span-7 @5xl:!col-span-4"
        :class="{
          '@5xl:!col-span-4': isSwapGroup,
          '@5xl:!col-span-8': !isSwapGroup,
        }"
        min-height="80"
      >
        <HistoryEventNote
          v-if="compactNotes"
          :notes="compactNotes"
          :chain="getChain(events[0].location)"
          :amount="events.map(item => item.amount)"
        />
      </LazyLoader>

      <LazyLoader
        v-if="!shouldExpand && !hideActions"
        key="history-event-actions"
        class="py-2 @5xl:!py-4 col-span-10 @md:col-span-3"
        min-height="40"
      >
        <HistoryEventsListItemAction
          :item="primaryEvent"
          :index="0"
          :events="allEvents"
          :can-unlink="canUnlink"
          :collapsed="!shouldExpand"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @show:missing-rule-action="emit('show:missing-rule-action', $event)"
          @unlink-event="emit('unlink-event', { groupIdentifier: primaryEvent.groupIdentifier })"
        />
      </LazyLoader>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.transition-wrapper .list-move,
.transition-wrapper .list-enter-active,
.transition-wrapper .list-leave-active {
  @apply transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)];
}

.transition-wrapper .list-enter-from,
.transition-wrapper .list-leave-to {
  @apply opacity-0;
}

.transition-wrapper .list-leave-active {
  @apply absolute w-full;
}

.transition-wrapper .list-leave-active[data-subtype="fee"] {
  @apply !transition-none;
}
</style>
