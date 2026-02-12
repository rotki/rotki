<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { getHighlightClass, type HighlightType } from '@/composables/history/events/use-history-events-filters';
import { useHistoryEventItem } from '../composables/use-history-event-item';

const props = withDefaults(defineProps<{
  event: HistoryEventEntry;
  index: number;
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
}>();

const { event } = toRefs(props);

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
  event,
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
    class="p-3 border-b border-default bg-white dark:bg-dark-surface contain-content transition-all"
    :class="[
      { 'opacity-50': hiddenEvent },
      highlight && getHighlightClass(highlightType),
    ]"
  >
    <!-- Top row: Checkbox, Location + Event Type + Timestamp -->
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
          :event="event"
          :chain="chain"
          :group-location-label="groupLocationLabel"
          :highlight="highlight"
          class="min-w-0 flex-1"
        />
      </div>
    </div>

    <!-- Middle row: Asset & Amount -->
    <div class="mb-2">
      <HistoryEventAsset
        :event="event"
        @refresh="emit('refresh')"
      />
    </div>

    <!-- Bottom row: Notes + Actions -->
    <div class="flex items-start justify-between gap-2">
      <HistoryEventNote
        :notes="notes"
        :amount="event.amount"
        :asset="event.asset"
        :chain="chain"
        :counterparty="counterparty"
        :validator-index="validatorIndex"
        :block-number="blockNumber"
        :extra-data="extraData"
        class="flex-1 min-w-0 overflow-hidden line-clamp-2 text-sm text-rui-text-secondary"
      />

      <HistoryEventsListItemAction
        v-if="!hideActions"
        :item="event"
        :index="index"
        :complete-group-events="completeGroupEvents"
        class="shrink-0"
        :class="{ 'opacity-50': !hasMissingRule }"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      />
    </div>
  </div>

  <!-- Row Layout -->
  <div
    v-else
    class="h-[72px] flex items-center gap-4 border-b border-default px-4 pl-8 group/row contain-content"
    :class="[
      { 'opacity-50': hiddenEvent },
      highlight && getHighlightClass(highlightType),
    ]"
  >
    <RuiCheckbox
      v-if="showCheckbox"
      v-model="isSelectedModel"
      color="primary"
      hide-details
      :disabled="isCheckboxDisabled"
      class="shrink-0 -ml-2"
    />

    <HistoryEventType
      :event="event"
      :chain="chain"
      :group-location-label="groupLocationLabel"
      :highlight="highlight"
      class="w-44 xl:w-52 shrink-0"
    />

    <HistoryEventAsset
      :event="event"
      class="w-60 shrink-0"
      @refresh="emit('refresh')"
    />

    <HistoryEventNote
      :notes="notes"
      :amount="event.amount"
      :asset="event.asset"
      :chain="chain"
      :counterparty="counterparty"
      :validator-index="validatorIndex"
      :block-number="blockNumber"
      :extra-data="extraData"
      class="flex-1 min-w-0 overflow-hidden line-clamp-2"
    />

    <HistoryEventsListItemAction
      v-if="!hideActions"
      :item="event"
      :index="index"
      :complete-group-events="completeGroupEvents"
      class="w-24 shrink-0 transition-opacity"
      :class="{ 'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100': !hasMissingRule }"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
    />
  </div>
</template>
