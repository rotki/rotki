<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { HistoryEventDeletePayload, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import type { HistoryEventNoteContext } from '@/modules/history/events/use-history-event-note';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import AccountingOverlayCell from '@/modules/history/balances/AccountingOverlayCell.vue';
import { getMatchedMovementIgnoreIds } from '@/modules/history/event-utils';
import { getHighlightClass, type HighlightType } from '@/modules/history/events/action-types';
import HistoryEventsExpandButton from '@/modules/history/events/components/HistoryEventsExpandButton.vue';
import HistoryEventsGroupToggle from '@/modules/history/events/components/HistoryEventsGroupToggle.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/modules/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/modules/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/modules/history/events/HistoryEventType.vue';
import { injectHistoryEventsSelection } from '@/modules/history/events/use-history-events-selection-context';
import { useHistoryMatchedMovementItem } from '../use-history-matched-movement-item';

const { events: eventsProp, variant = 'row' } = defineProps<{
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
  variant?: 'row' | 'card';
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'unlink-event': [data: HistoryEventUnlinkPayload];
  'refresh': [];
  'toggle-expand': [];
}>();

const events = computed<HistoryEventEntry[]>(() => eventsProp);

const { t } = useI18n({ useScope: 'global' });

const selection = injectHistoryEventsSelection();

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

function unlink(): void {
  emit('unlink-event', {
    identifier: get(primaryEvent).identifier,
    ignoredIdentifiers: getMatchedMovementIgnoreIds(get(events)),
    type: 'asset-movement',
  });
}

const noteContext = computed<HistoryEventNoteContext>(() => ({
  amount: get(primaryEvent).amount,
  asset: get(primaryEvent).asset,
}));
</script>

<template>
  <div
    v-if="isCard"
    data-testid="history-event-movement"
    :data-event-id="eventsProp[0]?.identifier"
    class="h-34 p-3 flex flex-col gap-2 overflow-hidden border-b border-default bg-rui-background contain-content transition-all"
    :class="[
      { 'opacity-50': primaryEvent.ignoredInAccounting },
      highlight && getHighlightClass(highlightType),
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
        :event="primaryEvent"
        :group-location-label="groupLocationLabel"
        :highlight="highlight"
        class="min-w-0 flex-1"
      >
        <template #append>
          <HistoryEventsExpandButton
            data-testid="movement-expand"
            :count="events.length"
            @expand="emit('toggle-expand')"
          />
        </template>
      </HistoryEventType>

      <HistoryEventAsset
        :event="primaryEvent"
        class="w-40 sm:w-48 shrink-0"
        @refresh="emit('refresh')"
      />
    </div>

    <div class="flex-1 min-h-0 flex items-start justify-between gap-2">
      <HistoryEventNote
        :notes="compactNotes"
        :context="noteContext"
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
        @unlink-event="unlink()"
      />
    </div>
  </div>

  <div
    v-else
    data-testid="history-event-movement"
    :data-event-id="eventsProp[0]?.identifier"
    class="h-[72px] flex items-center gap-4 border-b border-default px-4 group/row relative contain-content transition-colors hover:bg-rui-grey-100 dark:hover:bg-white/5"
    :class="[
      showCheckbox ? 'pl-16' : 'pl-6',
      { 'opacity-50': primaryEvent.ignoredInAccounting },
    ]"
  >
    <RuiCheckbox
      v-if="showCheckbox"
      v-model="isSelectedModel"
      color="primary"
      hide-details
      :disabled="isCheckboxDisabled"
      class="absolute left-4 top-1/2 -translate-y-1/2"
    />

    <HistoryEventsGroupToggle
      data-testid="movement-expand"
      :count="events.length"
      :selecting="showCheckbox"
      @toggle="emit('toggle-expand')"
    />

    <HistoryEventType
      :event="primaryEvent"
      :highlight="highlight"
      hide-state-chips
      :group-location-label="groupLocationLabel"
      class="w-56 shrink-0"
    >
      <template #append>
        <span class="text-xs text-rui-text-secondary whitespace-nowrap">
          {{ t('history_events_list_swap.event_count', { count: events.length }) }}
        </span>
      </template>
    </HistoryEventType>

    <HistoryEventAsset
      :event="primaryEvent"
      class="w-56 xl:w-60 shrink-0"
      @refresh="emit('refresh')"
    />

    <HistoryEventNote
      :notes="compactNotes"
      :context="noteContext"
      :chain="chain"
      class="flex-1 min-w-0 overflow-hidden self-center line-clamp-2"
    />

    <AccountingOverlayCell :event="primaryEvent" />

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
      @unlink-event="unlink()"
    />
  </div>
</template>
