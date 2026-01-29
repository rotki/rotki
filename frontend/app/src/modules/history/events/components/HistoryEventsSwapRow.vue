<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
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
  'refresh': [];
  'toggle-expand': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChain } = useSupportedChains();
const { getAssetSymbol } = useAssetInfoRetrieval();

const ASSET_RESOLUTION_OPTIONS: AssetResolutionOptions = { collectionParent: false };

const primaryEvent = computed<HistoryEventEntry>(() => props.events[0]);

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

// All event IDs in this swap for selection
const swapEventIds = computed<number[]>(() => props.events.map(e => e.identifier));

const isSelected = computed<boolean>({
  get() {
    if (!props.selection)
      return false;
    // A swap is selected if all its events are selected
    return get(swapEventIds).every(id => props.selection!.isEventSelected(id));
  },
  set(value: boolean) {
    if (value !== get(isSelected))
      props.selection?.actions.toggleSwap(get(swapEventIds));
  },
});

// Separate spend and receive events
const spendEvents = computed<HistoryEventEntry[]>(() =>
  props.events.filter(e => e.eventSubtype === 'spend'),
);

const receiveEvents = computed<HistoryEventEntry[]>(() =>
  props.events.filter(e => e.eventSubtype === 'receive'),
);

// First spend/receive for visual display
const spendEvent = computed<HistoryEventEntry | undefined>(() => get(spendEvents)[0]);
const receiveEvent = computed<HistoryEventEntry | undefined>(() => get(receiveEvents)[0]);

// Check if multi-swap (multiple spend or receive events)
const isMultiSpend = computed<boolean>(() => get(spendEvents).length > 1);
const isMultiReceive = computed<boolean>(() => get(receiveEvents).length > 1);

const counterparty = computed<string | undefined>(() => {
  const ev = get(primaryEvent);
  return 'counterparty' in ev ? (ev.counterparty ?? undefined) : undefined;
});

// Build compact swap notes (handles multi-swap)
const compactNotes = computed<string | undefined>(() => {
  const spend = get(spendEvents);
  const receive = get(receiveEvents);

  if (spend.length === 0 || receive.length === 0)
    return undefined;

  // For multi-swap, show "X asset" instead of specific amount
  const spendNotes = spend.length === 1
    ? {
        spendAmount: spend[0].amount,
        spendAsset: getAssetSymbol(spend[0].asset, ASSET_RESOLUTION_OPTIONS),
      }
    : {
        spendAmount: spend.length,
        spendAsset: 'assets',
      };

  const receiveNotes = receive.length === 1
    ? {
        receiveAmount: receive[0].amount,
        receiveAsset: getAssetSymbol(receive[0].asset, ASSET_RESOLUTION_OPTIONS),
      }
    : {
        receiveAmount: receive.length,
        receiveAsset: 'assets',
      };

  const notes = t('history_events_list_swap.swap_description', {
    ...spendNotes,
    ...receiveNotes,
  });

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
        class="size-5 relative top-3 -left-2 z-[6]"
        @click="emit('toggle-expand')"
      >
        <RuiIcon
          class="hidden group-hover/row:block"
          name="lu-unfold-vertical"
          size="14"
        />
        <span class="group-hover/row:hidden text-xs">{{ events.length }}</span>
      </RuiButton>

      <!-- Swap icon + type (w-44 to match detail row event type) -->
      <HistoryEventType
        :event="primaryEvent"
        :chain="chain"
        :group-location-label="groupLocationLabel"
        :highlight="highlight"
        icon="lu-arrow-right-left"
        hide-state-chips
        class="w-44 shrink-0 self-center"
      />
    </div>

    <!-- Spend asset (w-52 to match detail row asset column) -->
    <div class="relative w-60 shrink-0">
      <HistoryEventAsset
        v-if="spendEvent"
        :event="spendEvent"
        @refresh="emit('refresh')"
      />
      <span
        v-if="isMultiSpend"
        class="absolute -top-1 -right-1 bg-rui-primary text-white text-[10px] font-medium rounded-full size-4 flex items-center justify-center"
      >
        +{{ spendEvents.length - 1 }}
      </span>
    </div>

    <!-- Arrow + Receive + Notes (aligned with notes column of detail rows) -->
    <div class="flex items-center gap-2 flex-1 min-w-0">
      <!-- Arrow -->
      <div class="shrink-0 size-6 rounded-full bg-rui-grey-200 dark:bg-rui-grey-700 flex items-center justify-center">
        <RuiIcon
          class="text-rui-grey-500 dark:text-rui-grey-400"
          name="lu-arrow-right"
          size="14"
        />
      </div>

      <!-- Receive asset(s) -->
      <div class="relative shrink-0">
        <HistoryEventAsset
          v-if="receiveEvent"
          :event="receiveEvent"
          @refresh="emit('refresh')"
        />
        <span
          v-if="isMultiReceive"
          class="absolute -top-1 -right-1 bg-rui-success text-white text-[10px] font-medium rounded-full size-4 flex items-center justify-center"
        >
          +{{ receiveEvents.length - 1 }}
        </span>
      </div>

      <!-- Notes -->
      <HistoryEventNote
        :notes="compactNotes"
        :chain="chain"
        :amount="events.map(item => item.amount)"
        :counterparty="counterparty"
        class="flex-1 min-w-0 overflow-hidden self-center line-clamp-2"
      />
    </div>

    <!-- Actions -->
    <HistoryEventsListItemAction
      v-if="!hideActions"
      :item="primaryEvent"
      :index="0"
      :events="allEvents"
      class="w-24 shrink-0 self-center transition-opacity"
      :class="{
        'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100': !hasMissingRule,
      }"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
    />
  </div>
</template>
