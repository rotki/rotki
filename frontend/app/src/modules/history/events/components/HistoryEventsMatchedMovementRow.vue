<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { isEventMissingAccountingRule } from '@/utils/history/events';

const props = defineProps<{
  events: HistoryEventEntry[];
  allEvents: HistoryEventEntry[];
  groupLocationLabel?: string;
  hideActions?: boolean;
  highlight?: boolean;
  selection?: UseHistoryEventsSelectionModeReturn;
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'unlink-event': [data: HistoryEventUnlinkPayload];
  'refresh': [];
  'toggle-expand': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChain } = useSupportedChains();
const { getAssetSymbol } = useAssetInfoRetrieval();

const ASSET_RESOLUTION_OPTIONS: AssetResolutionOptions = { collectionParent: false };

// For asset movements, use the first non-fee asset movement event as primary
const primaryEvent = computed<HistoryEventEntry>(() => {
  const assetMovementEvent = props.events.find(
    item => item.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT && item.eventSubtype !== 'fee',
  );
  return assetMovementEvent ?? props.events[0];
});

const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(get(primaryEvent)));

const chain = computed(() => getChain(get(primaryEvent).location));

const showCheckbox = computed<boolean>(() => {
  if (!props.selection)
    return false;
  return get(props.selection.isSelectionMode);
});

const isCheckboxDisabled = computed<boolean>(() => {
  if (!props.selection)
    return false;
  return get(props.selection.isSelectAllMatching);
});

// All event IDs in this movement for selection
const movementEventIds = computed<number[]>(() => props.events.map(e => e.identifier));

const isSelected = computed<boolean>({
  get() {
    if (!props.selection)
      return false;
    // A movement is selected if all its events are selected
    return get(movementEventIds).every(id => props.selection!.isEventSelected(id));
  },
  set(value: boolean) {
    if (value !== get(isSelected))
      props.selection?.actions.toggleSwap(get(movementEventIds));
  },
});

// Check if this movement can be unlinked
const canUnlink = computed<boolean>(() => {
  const ev = get(primaryEvent);
  return !!ev.actualGroupIdentifier;
});

// Build compact notes for asset movements with fee
const compactNotes = computed<string | undefined>(() => {
  const primary = get(primaryEvent);
  // Secondary event is the one that's NOT an asset movement event (e.g., EVM event, Solana event)
  const secondary = props.events.find(
    item => item.entryType !== HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
  );

  const amount = primary.amount;
  const asset = getAssetSymbol(primary.asset, ASSET_RESOLUTION_OPTIONS);
  const locationLabel = primary.locationLabel ?? '';
  const address = secondary?.locationLabel ?? '';

  const notes = primary.eventType === 'deposit'
    ? t('asset_movement_matching.compact_notes.deposit', { address, amount, asset, locationLabel })
    : t('asset_movement_matching.compact_notes.withdraw', { address, amount, asset, locationLabel });

  // Append fee if exists
  const fee = props.events.filter(item => item.eventSubtype === 'fee');
  if (fee.length === 0)
    return notes;

  const feeText = fee.map(item => `${item.amount} ${getAssetSymbol(item.asset, ASSET_RESOLUTION_OPTIONS)}`).join('; ');
  return t('history_events_list_swap.fee_description', { feeText, notes });
});
</script>

<template>
  <div
    class="h-20 flex items-center gap-4 border-b border-default px-4 pl-8 group/row relative contain-content"
    :class="{ 'opacity-50': primaryEvent.ignoredInAccounting }"
  >
    <!-- Checkbox for selection mode (aligned with detail row) -->
    <RuiCheckbox
      v-if="showCheckbox"
      v-model="isSelected"
      color="primary"
      hide-details
      :disabled="isCheckboxDisabled"
      class="shrink-0 -ml-2"
    />

    <div>
      <!-- Expand button (absolute positioned at left) -->
      <RuiButton
        size="sm"
        icon
        color="primary"
        class="size-5 absolute top-3 -left-2 z-[6]"
        @click="emit('toggle-expand')"
      >
        <RuiIcon
          class="hidden group-hover/row:block"
          name="lu-unfold-vertical"
          size="14"
        />
        <span class="group-hover/row:hidden text-xs">{{ events.length }}</span>
      </RuiButton>

      <!-- Event type - uses primary event's type (EXCHANGE DEPOSIT/WITHDRAW) -->
      <!-- Hide state chips and account in collapsed view -->
      <HistoryEventType
        :event="primaryEvent"
        :chain="chain"
        :highlight="highlight"
        hide-state-chips
        :group-location-label="groupLocationLabel"
        class="w-44 shrink-0 self-center"
      />
    </div>

    <!-- Asset & Amount -->
    <HistoryEventAsset
      :event="primaryEvent"
      class="w-60 shrink-0"
      @refresh="emit('refresh')"
    />

    <!-- Notes with fee included -->
    <HistoryEventNote
      :notes="compactNotes"
      :amount="primaryEvent.amount"
      :asset="primaryEvent.asset"
      :chain="chain"
      class="flex-1 min-w-0 overflow-hidden self-center line-clamp-2"
    />

    <!-- Actions -->
    <HistoryEventsListItemAction
      v-if="!hideActions"
      :item="primaryEvent"
      :index="0"
      :events="allEvents"
      :can-unlink="canUnlink"
      class="w-24 shrink-0 self-center transition-opacity"
      :class="{
        'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100': !hasMissingRule,
      }"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      @unlink-event="emit('unlink-event', { groupIdentifier: primaryEvent.groupIdentifier })"
    />
  </div>
</template>
