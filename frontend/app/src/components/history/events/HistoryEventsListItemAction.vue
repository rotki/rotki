<script setup lang="ts">
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { DependentHistoryEvent, HistoryEvent, HistoryEventEntry } from '@/types/history/events';
import RowActions from '@/components/helper/RowActions.vue';
import HistoryEventAction from '@/components/history/events/HistoryEventAction.vue';
import { isDependentHistoryEvent } from '@/modules/history/management/forms/form-guards';
import {
  isAssetMovementEvent,
  isEventAccountingRuleProcessed,
  isEventMissingAccountingRule,
  isEvmEvent,
} from '@/utils/history/events';
import { HistoryEventEntryType } from '@rotki/common';

const props = defineProps<{
  item: HistoryEventEntry;
  index: number;
  events: HistoryEventEntry[];
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: { canDelete: boolean; item: HistoryEventEntry }];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const { t } = useI18n();

function hideActions(item: HistoryEventEntry, index: number): boolean {
  const isSwapButNotSpend = item.entryType === HistoryEventEntryType.SWAP_EVENT && index !== 0;
  const isAssetMovementFee = isAssetMovementEvent(item) && item.eventSubtype === 'fee';
  return isAssetMovementFee || isSwapButNotSpend;
}

function getEmittedEvent(item: HistoryEvent): HistoryEventEditData {
  if (isDependentHistoryEvent(item)) {
    return {
      eventsInGroup: props.events as DependentHistoryEvent[],
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
  emit('delete-event', {
    canDelete: isEvmEvent(item) ? props.events.length > 1 : true,
    item,
  });
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
      v-else-if="!isEventAccountingRuleProcessed(item)"
      :event="item"
    />
    <div
      v-else
      class="w-10 h-10"
    />
  </RowActions>
</template>
