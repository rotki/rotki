<script setup lang="ts">
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type {
  GroupEditableHistoryEvents,
  HistoryEvent,
  HistoryEventEntry,
} from '@/types/history/events/schemas';
import RowActions from '@/components/helper/RowActions.vue';
import HistoryEventAction from '@/components/history/events/HistoryEventAction.vue';
import {
  isGroupEditableHistoryEvent,
  isSwapTypeEvent,
} from '@/modules/history/management/forms/form-guards';
import {
  isAssetMovementEvent,
  isEventMissingAccountingRule,
  isEvmEvent,
} from '@/utils/history/events';

const props = defineProps<{
  item: HistoryEventEntry;
  index: number;
  events: HistoryEventEntry[];
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const { t } = useI18n({ useScope: 'global' });

function hideActions(item: HistoryEventEntry, index: number): boolean {
  const isSwapButNotSpend = isSwapTypeEvent(item.entryType) && index !== 0;
  const isAssetMovementFee = isAssetMovementEvent(item) && item.eventSubtype === 'fee';
  return isAssetMovementFee || isSwapButNotSpend;
}

function getEmittedEvent(item: HistoryEvent): HistoryEventEditData {
  if (isGroupEditableHistoryEvent(item) || isSwapTypeEvent(item.entryType)) {
    return {
      eventsInGroup: props.events as GroupEditableHistoryEvents[],
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
  const isSingleEvmEvent = isEvmEvent(item) && props.events.length === 1;
  const payload: HistoryEventDeletePayload = isSingleEvmEvent
    ? {
        event: item,
        type: 'ignore',
      }
    : {
        ids: isGroupEditableHistoryEvent(item) || isSwapTypeEvent(item.entryType) ? props.events.map(event => event.identifier) : [item.identifier],
        type: 'delete',
      };

  emit('delete-event', payload);
}
</script>

<template>
  <RowActions
    align="end"
    :delete-tooltip="t('transactions.events.actions.delete')"
    :edit-tooltip="t('transactions.events.actions.edit')"
    :no-delete="hideActions(item, index)"
    :no-edit="hideActions(item, index)"
    @edit-click="editEvent(item)"
    @delete-click="deleteEvent(item)"
  >
    <RuiTooltip
      v-if="isEventMissingAccountingRule(item)"
      :popper="{ placement: 'top', offsetDistance: 0 }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
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
      </template>
      {{ t('actions.history_events.missing_rule.title') }}
    </RuiTooltip>
    <HistoryEventAction
      v-else
      :event="item"
    />
  </RowActions>
</template>
