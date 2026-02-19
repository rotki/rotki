<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { getHighlightClass, type HighlightType } from '@/composables/history/events/types';
import { useHistorySwapItem } from '../composables/use-history-swap-item';

const props = withDefaults(defineProps<{
  events: HistoryEventEntry[];
  /**
   * All events in the same group, including hidden and ignored events.
   * This complete set is required for correctly editing grouped events (e.g., swap events).
   */
  completeGroupEvents: HistoryEventEntry[];
  groupLocationLabel?: string;
  hideActions?: boolean;
  highlight?: boolean;
  highlightType?: HighlightType;
  selection?: UseHistoryEventsSelectionModeReturn;
  variant?: 'row' | 'card';
}>(), {
  variant: 'row',
});

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'refresh': [];
  'toggle-expand': [];
}>();

const events = computed<HistoryEventEntry[]>(() => props.events);

const {
  chain,
  compactNotes,
  counterparty,
  isCheckboxDisabled,
  isMultiReceive,
  isMultiSpend,
  isReceiveHidden,
  isSelected,
  isSpendHidden,
  primaryEvent,
  receiveEvent,
  receiveEvents,
  showCheckbox,
  spendEvent,
  spendEvents,
  toggleSelected,
} = useHistorySwapItem({
  events,
  selection: props.selection,
});

const isSelectedModel = computed<boolean>({
  get: () => get(isSelected),
  set: (value: boolean) => {
    if (value !== get(isSelected))
      toggleSelected();
  },
});

const isCard = computed<boolean>(() => props.variant === 'card');
</script>

<template>
  <!-- Card Layout -->
  <div
    v-if="isCard"
    data-cy="history-event-swap"
    class="p-3 border-b border-default bg-white dark:bg-dark-surface contain-content transition-all"
    :class="[
      { 'opacity-50': primaryEvent.ignoredInAccounting },
      highlight && getHighlightClass(highlightType),
    ]"
  >
    <!-- Top row: Checkbox, Location, Swap badge, Event count, Timestamp -->
    <div class="flex items-center justify-between gap-2 mb-2">
      <div class="flex items-center gap-2 min-w-0">
        <RuiCheckbox
          v-if="showCheckbox"
          v-model="isSelectedModel"
          color="primary"
          hide-details
          :disabled="isCheckboxDisabled"
          class="shrink-0"
        />

        <HistoryEventType
          :event="primaryEvent"
          :chain="chain"
          :group-location-label="groupLocationLabel"
          :highlight="highlight"
          class="min-w-0 flex-1"
        />

        <RuiButton
          size="sm"
          icon
          color="primary"
          class="size-5"
          @click="emit('toggle-expand')"
        >
          <RuiIcon
            class="hidden group-hover:block"
            name="lu-unfold-vertical"
            size="14"
          />
          <span class="group-hover:hidden text-xs">{{ events.length }}</span>
        </RuiButton>
      </div>
    </div>

    <!-- Middle row: Spend → Receive -->
    <div class="flex items-center gap-2 mb-2">
      <div
        class="relative flex-1 min-w-0"
        :class="{ 'opacity-50': isSpendHidden }"
      >
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

      <div class="shrink-0 size-6 rounded-full bg-rui-grey-200 dark:bg-rui-grey-700 flex items-center justify-center">
        <RuiIcon
          class="text-rui-grey-500 dark:text-rui-grey-400"
          name="lu-arrow-right"
          size="14"
        />
      </div>

      <div
        class="relative flex-1 min-w-0"
        :class="{ 'opacity-50': isReceiveHidden }"
      >
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
    </div>

    <!-- Bottom row: Notes + Actions -->
    <div class="flex items-start justify-between gap-2">
      <HistoryEventNote
        :notes="compactNotes"
        :chain="chain"
        :amount="events.map(item => item.amount)"
        :counterparty="counterparty"
        class="flex-1 min-w-0 overflow-hidden line-clamp-2 text-sm text-rui-text-secondary"
      />

      <HistoryEventsListItemAction
        v-if="!hideActions"
        :item="primaryEvent"
        :index="0"
        :complete-group-events="completeGroupEvents"
        class="shrink-0"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      />
    </div>
  </div>

  <!-- Row Layout -->
  <div
    v-else
    data-cy="history-event-swap"
    class="h-[72px] flex items-center gap-4 border-b border-default px-4 pl-6 group/row relative contain-content"
    :class="{ 'opacity-50': primaryEvent.ignoredInAccounting }"
  >
    <RuiCheckbox
      v-if="showCheckbox"
      v-model="isSelectedModel"
      color="primary"
      hide-details
      :disabled="isCheckboxDisabled"
      class="shrink-0 -ml-2"
    />

    <div class="relative -top-2">
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

      <HistoryEventType
        :event="primaryEvent"
        :chain="chain"
        :group-location-label="groupLocationLabel"
        :highlight="highlight"
        icon="lu-arrow-right-left"
        hide-state-chips
        class="w-56 shrink-0 self-center"
      />
    </div>

    <div
      class="relative w-56 xl:w-60 shrink-0"
      :class="{ 'opacity-50': isSpendHidden }"
    >
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

    <div class="flex items-center gap-2 flex-1 min-w-0">
      <div class="shrink-0 size-6 rounded-full bg-rui-grey-200 dark:bg-rui-grey-700 flex items-center justify-center">
        <RuiIcon
          class="text-rui-grey-500 dark:text-rui-grey-400"
          name="lu-arrow-right"
          size="14"
        />
      </div>

      <div
        class="relative shrink-0"
        :class="{ 'opacity-50': isReceiveHidden }"
      >
        <HistoryEventAsset
          v-if="receiveEvent"
          :event="receiveEvent"
          class="w-56 xl:w-60"
          @refresh="emit('refresh')"
        />
        <span
          v-if="isMultiReceive"
          class="absolute -top-1 -right-1 bg-rui-success text-white text-[10px] font-medium rounded-full size-4 flex items-center justify-center"
        >
          +{{ receiveEvents.length - 1 }}
        </span>
      </div>

      <HistoryEventNote
        :notes="compactNotes"
        :chain="chain"
        :amount="events.map(item => item.amount)"
        :counterparty="counterparty"
        class="flex-1 min-w-0 overflow-hidden self-center line-clamp-2"
      />
    </div>

    <HistoryEventsListItemAction
      v-if="!hideActions"
      :item="primaryEvent"
      :index="0"
      :complete-group-events="completeGroupEvents"
      collapse-action
      class="shrink-0 self-center"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
    />
  </div>
</template>
