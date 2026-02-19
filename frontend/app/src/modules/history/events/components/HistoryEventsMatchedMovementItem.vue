<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { getHighlightClass, type HighlightType } from '@/composables/history/events/types';
import { useHistoryMatchedMovementItem } from '../composables/use-history-matched-movement-item';

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
  'unlink-event': [data: HistoryEventUnlinkPayload];
  'refresh': [];
  'toggle-expand': [];
}>();

const events = computed<HistoryEventEntry[]>(() => props.events);

const {
  canUnlink,
  chain,
  compactNotes,
  hasMissingRule,
  isCheckboxDisabled,
  isSelected,
  primaryEvent,
  showCheckbox,
  toggleSelected,
} = useHistoryMatchedMovementItem({
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
    data-cy="history-event-movement"
    class="p-3 border-b border-default bg-white dark:bg-dark-surface contain-content group transition-all"
    :class="[
      { 'opacity-50': primaryEvent.ignoredInAccounting },
      highlight && getHighlightClass(highlightType),
    ]"
  >
    <!-- Top row: Checkbox, Location, Movement badge, Event count, Timestamp -->
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

    <!-- Middle row: Asset & Amount -->
    <div class="mb-2">
      <HistoryEventAsset
        :event="primaryEvent"
        @refresh="emit('refresh')"
      />
    </div>

    <!-- Bottom row: Notes + Actions -->
    <div class="flex items-start justify-between gap-2">
      <HistoryEventNote
        :notes="compactNotes"
        :amount="primaryEvent.amount"
        :asset="primaryEvent.asset"
        :chain="chain"
        class="flex-1 min-w-0 overflow-hidden line-clamp-2 text-sm text-rui-text-secondary"
      />

      <HistoryEventsListItemAction
        v-if="!hideActions"
        :item="primaryEvent"
        :index="0"
        :complete-group-events="completeGroupEvents"
        :can-unlink="canUnlink"
        class="shrink-0"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
        @unlink-event="emit('unlink-event', { identifier: primaryEvent.identifier })"
      />
    </div>
  </div>

  <!-- Row Layout -->
  <div
    v-else
    data-cy="history-event-movement"
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

    <div class="relative -top-2.5">
      <RuiButton
        size="sm"
        icon
        color="primary"
        class="size-5 relative top-4 -left-2 z-[6]"
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
        :highlight="highlight"
        hide-state-chips
        :group-location-label="groupLocationLabel"
        class="w-56 shrink-0 self-center"
      />
    </div>

    <HistoryEventAsset
      :event="primaryEvent"
      class="w-56 xl:w-60 shrink-0"
      @refresh="emit('refresh')"
    />

    <HistoryEventNote
      :notes="compactNotes"
      :amount="primaryEvent.amount"
      :asset="primaryEvent.asset"
      :chain="chain"
      class="flex-1 min-w-0 overflow-hidden self-center line-clamp-2"
    />

    <HistoryEventsListItemAction
      v-if="!hideActions"
      :item="primaryEvent"
      :index="0"
      :complete-group-events="completeGroupEvents"
      :can-unlink="canUnlink"
      class="w-24 shrink-0 self-center transition-opacity"
      :class="{ 'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100': !hasMissingRule }"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      @unlink-event="emit('unlink-event', { identifier: primaryEvent.identifier })"
    />
  </div>
</template>
