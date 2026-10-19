<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventNoteContext } from '@/modules/history/events/use-history-event-note';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import AccountingOverlayCell from '@/modules/history/balances/AccountingOverlayCell.vue';
import { getHighlightClass, type HighlightType } from '@/modules/history/events/action-types';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/modules/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/modules/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/modules/history/events/HistoryEventType.vue';
import { injectHistoryEventsSelection } from '@/modules/history/events/use-history-events-selection-context';
import { useHistoryEventItem } from '../use-history-event-item';

const {
  event,
  index,
  completeGroupEvents,
  groupLocationLabel,
  linkedLeg,
  hideActions,
  highlightType,
  variant = 'row',
} = defineProps<{
  event: HistoryEventEntry;
  index: number;
  /**
   * All events in the same group, including hidden and ignored events.
   * This complete set is required for correctly editing grouped events (e.g., swap events).
   */
  completeGroupEvents: HistoryEventEntry[];
  groupLocationLabel?: string;
  /** Set when this row is a sub-event of an expanded linked (matched) movement. */
  linkedLeg?: boolean;
  hideActions?: boolean;
  /** The highlight colour. Its presence is what highlights the row. */
  highlightType?: HighlightType;
  variant?: 'row' | 'card';
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'refresh': [];
}>();

const selection = injectHistoryEventsSelection();

const {
  blockNumber,
  chain,
  counterparty,
  extraData,
  hasMissingRule,
  hiddenEvent,
  isCheckboxDisabled,
  isSelected,
  notes,
  showCheckbox,
  toggleSelected,
  validatorIndex,
} = useHistoryEventItem({
  event: () => event,
  groupEvents: () => completeGroupEvents,
  selection,
});

const isSelectedModel = computed<boolean>({
  get: () => get(isSelected),
  set: (value: boolean) => {
    if (value !== get(isSelected))
      toggleSelected();
  },
});

const isCard = computed<boolean>(() => variant === 'card');

/**
 * Whether the row layout has built its action cluster yet.
 *
 * The cluster carries a RuiMenu, whose `useElementSize` reads `offsetWidth` on mount and so forces
 * a synchronous layout right after the virtual list mutated the DOM. Over a scroll that was the
 * table's largest source of forced reflow. It is invisible until the row is hovered, so it is built
 * on first hover, or when focus enters the row, which is how a keyboard reaches it. Once built it
 * stays: unmounting on leave would pay the cost again on the next hover.
 *
 * The card layout does not gate: it is the narrow-viewport variant, where there is no hover.
 */
const actionsRevealed = shallowRef<boolean>(false);

const showActions = computed<boolean>(() => !hideActions && (get(hasMissingRule) || get(actionsRevealed)));

function revealActions(): void {
  set(actionsRevealed, true);
}

const noteContext = computed<HistoryEventNoteContext>(() => ({
  amount: event.amount,
  asset: event.asset,
  blockNumber: get(blockNumber),
  counterparty: get(counterparty),
  extraData: get(extraData),
  validatorIndex: get(validatorIndex),
}));
</script>

<template>
  <div
    v-if="isCard"
    data-testid="history-event-row"
    :data-event-id="event.identifier"
    class="h-34 p-3 flex flex-col gap-2 overflow-hidden border-b border-default bg-rui-background contain-content transition-all"
    :class="[
      { 'opacity-50': hiddenEvent },
      getHighlightClass(highlightType),
    ]"
  >
    <div class="h-14 shrink-0 flex items-center gap-2 min-w-0">
      <RuiCheckbox
        v-if="showCheckbox"
        v-model="isSelectedModel"
        color="primary"
        hide-details
        :disabled="isCheckboxDisabled"
        class="shrink-0"
      />

      <HistoryEventType
        :event="event"
        :chain="chain"
        :group-location-label="groupLocationLabel"
        :linked-leg="linkedLeg"
        :highlight="!!highlightType"
        class="min-w-0 flex-1"
      />

      <HistoryEventAsset
        :event="event"
        class="w-40 sm:w-48 shrink-0"
        @refresh="emit('refresh')"
      />
    </div>

    <div class="flex-1 min-h-0 flex items-start justify-between gap-2">
      <HistoryEventNote
        :notes="notes"
        :context="noteContext"
        :chain="chain"
        class="flex-1 min-w-0 overflow-hidden line-clamp-2 text-sm text-rui-text-secondary"
      />

      <HistoryEventsListItemAction
        v-if="!hideActions"
        :item="event"
        :index="index"
        :complete-group-events="completeGroupEvents"
        class="shrink-0"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      />
    </div>
  </div>

  <div
    v-else
    data-testid="history-event-row"
    :data-event-id="event.identifier"
    class="h-[72px] flex items-center gap-4 border-b border-default px-4 group/row relative contain-content transition-colors hover:bg-rui-grey-100 dark:hover:bg-white/5"
    :class="[
      showCheckbox ? 'pl-16' : 'pl-6',
      { 'opacity-50': hiddenEvent },
      getHighlightClass(highlightType),
    ]"
    @pointerenter="revealActions()"
    @focusin="revealActions()"
  >
    <RuiCheckbox
      v-if="showCheckbox"
      v-model="isSelectedModel"
      color="primary"
      hide-details
      :disabled="isCheckboxDisabled"
      class="absolute left-4 top-1/2 -translate-y-1/2"
    />

    <HistoryEventType
      :event="event"
      :chain="chain"
      :group-location-label="groupLocationLabel"
      :linked-leg="linkedLeg"
      :highlight="!!highlightType"
      class="w-56 shrink-0"
    />

    <HistoryEventAsset
      :event="event"
      class="w-56 xl:w-60 shrink-0"
      @refresh="emit('refresh')"
    />

    <HistoryEventNote
      :notes="notes"
      :context="noteContext"
      :chain="chain"
      class="flex-1 min-w-0 overflow-hidden line-clamp-2"
    />

    <AccountingOverlayCell :event="event" />

    <HistoryEventsListItemAction
      v-if="showActions"
      :item="event"
      :index="index"
      :complete-group-events="completeGroupEvents"
      class="w-24 shrink-0 transition-opacity"
      :class="{ 'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100': !hasMissingRule }"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
    />
    <div
      v-else-if="!hideActions"
      class="w-24 shrink-0"
      aria-hidden="true"
    />
  </div>
</template>
