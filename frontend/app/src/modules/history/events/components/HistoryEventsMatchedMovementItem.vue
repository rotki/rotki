<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import DateDisplay from '@/components/display/DateDisplay.vue';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useHistoryMatchedMovementItem } from '../composables/use-history-matched-movement-item';

const props = withDefaults(defineProps<{
  events: HistoryEventEntry[];
  allEvents: HistoryEventEntry[];
  groupLocationLabel?: string;
  hideActions?: boolean;
  highlight?: boolean;
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
  eventTypeLabel,
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
    class="p-3 border-b border-default bg-white dark:bg-dark-surface contain-content"
    :class="{ 'opacity-50': primaryEvent.ignoredInAccounting }"
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

        <LocationIcon
          icon
          :item="primaryEvent.location"
          size="18px"
          class="shrink-0"
        />

        <div class="flex items-center gap-1.5 px-2 py-0.5 bg-rui-info/10 rounded text-rui-info text-sm font-medium">
          <RuiIcon
            :name="primaryEvent.eventType === 'deposit' ? 'lu-download' : 'lu-upload'"
            size="14"
          />
          <span>{{ eventTypeLabel }}</span>
        </div>

        <RuiButton
          size="sm"
          variant="outlined"
          class="!px-2 !py-0.5 !min-w-0"
          @click="emit('toggle-expand')"
        >
          <span class="text-xs">{{ events.length }}</span>
          <RuiIcon
            name="lu-unfold-vertical"
            size="12"
            class="ml-1"
          />
        </RuiButton>
      </div>

      <DateDisplay
        :timestamp="primaryEvent.timestamp"
        milliseconds
        class="text-xs text-rui-text-secondary shrink-0"
      />
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
        :events="allEvents"
        :can-unlink="canUnlink"
        class="shrink-0"
        :class="{ 'opacity-50': !hasMissingRule }"
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
    class="h-[72px] flex items-center gap-4 border-b border-default px-4 pl-8 group/row relative contain-content"
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
        class="w-44 xl:w-52 shrink-0 self-center"
      />
    </div>

    <HistoryEventAsset
      :event="primaryEvent"
      class="w-60 shrink-0"
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
      :events="allEvents"
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
