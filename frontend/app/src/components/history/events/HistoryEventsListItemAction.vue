<script setup lang="ts">
import type {
  GroupEditableHistoryEvents,
  HistoryEvent,
  HistoryEventEntry,
} from '@/modules/history/events/schemas';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import RowActions from '@/components/helper/RowActions.vue';
import HistoryEventAction from '@/components/history/events/HistoryEventAction.vue';
import {
  isAssetMovementEvent,
  isEventMissingAccountingRule,
  isEvmEvent,
} from '@/modules/history/event-utils';
import {
  hideDeleteAction,
  hideEditAction,
  shouldDeleteGroup,
} from '@/modules/history/events/event-action-visibility';
import {
  isGroupEditableHistoryEvent,
  isSwapTypeEvent,
} from '@/modules/history/management/forms/form-guards';

const { item, index, completeGroupEvents, canUnlink, collapsed, collapseAction } = defineProps<{
  item: HistoryEventEntry;
  index: number;
  /**
   * All events in the same group, including hidden and ignored events.
   * This complete set is required for correctly editing grouped events (e.g., swap events).
   */
  completeGroupEvents: HistoryEventEntry[];
  canUnlink?: boolean;
  collapsed?: boolean;
  collapseAction?: boolean;
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'unlink-event': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const COLLAPSE_ACTION_CLASSES = 'w-0 group-hover/row:w-auto 2xl:!w-24 2xl:opacity-0 2xl:group-hover/row:opacity-100 2xl:focus-within:opacity-100';

const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(item));

function getEmittedEvent(item: HistoryEvent): HistoryEventEditData {
  if (isSwapTypeEvent(item.entryType)) {
    return {
      eventsInGroup: completeGroupEvents as GroupEditableHistoryEvents[],
      type: 'edit-group',
    };
  }

  if (isGroupEditableHistoryEvent(item)) {
    const idx = completeGroupEvents.findIndex(e => e.identifier === item.identifier);
    const eventsInGroup: GroupEditableHistoryEvents[] = [item];
    const nextEvent = completeGroupEvents[idx + 1];
    if (nextEvent && isAssetMovementEvent(nextEvent) && nextEvent.eventSubtype === 'fee')
      eventsInGroup.push(nextEvent);

    return {
      eventsInGroup,
      type: 'edit-group',
    };
  }
  return {
    event: item,
    nextSequenceId: '',
    type: 'edit',
  };
}

function editEvent(item: HistoryEvent) {
  emit('edit-event', getEmittedEvent(item));
}

function deleteEvent(item: HistoryEventEntry) {
  const isSingleEvmEvent = isEvmEvent(item) && completeGroupEvents.length === 1;
  const payload: HistoryEventDeletePayload = isSingleEvmEvent
    ? {
        event: item,
        type: 'ignore',
      }
    : {
        ids: shouldDeleteGroup(item, index) ? completeGroupEvents.map(event => event.identifier) : [item.identifier],
        type: 'delete',
      };

  emit('delete-event', payload);
}
</script>

<template>
  <div
    class="flex items-center gap-1 justify-end"
    :class="{
      'transition-opacity overflow-hidden 2xl:overflow-visible': collapseAction,
      [COLLAPSE_ACTION_CLASSES]: collapseAction && !hasMissingRule,
    }"
  >
    <!-- Edit/Delete/Other actions - hidden on default when missing rule, visible on hover -->
    <RowActions
      :class="{
        'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100 transition-opacity': hasMissingRule && !collapseAction,
        [COLLAPSE_ACTION_CLASSES]: hasMissingRule && collapseAction,
      }"
      align="end"
      :delete-tooltip="t('transactions.events.actions.delete')"
      :edit-tooltip="t('transactions.events.actions.edit')"
      :no-delete="hideDeleteAction(item, index, completeGroupEvents)"
      :no-edit="hideEditAction(item, index)"
      @edit-click="editEvent(item)"
      @delete-click="deleteEvent(item)"
    >
      <RuiButton
        v-if="canUnlink && collapsed"
        :title="t('transactions.events.actions.unlink')"
        variant="text"
        icon
        @click="emit('unlink-event')"
      >
        <RuiIcon
          size="16"
          name="lu-unlink"
        />
      </RuiButton>
      <HistoryEventAction
        v-else-if="!hasMissingRule"
        :event="item"
        :can-unlink="canUnlink"
        @unlink="emit('unlink-event')"
      />
    </RowActions>

    <!-- Warning button - always visible when there's a missing rule (shown last/rightmost) -->
    <RuiButton
      v-if="hasMissingRule"
      :title="t('actions.history_events.missing_rule.title')"
      variant="text"
      color="warning"
      icon
      @click="emit('show:missing-rule-action', getEmittedEvent(item))"
    >
      <RuiIcon
        size="16"
        name="lu-info"
      />
    </RuiButton>
  </div>
</template>
