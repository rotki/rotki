<script setup lang="ts">
import type {
  HistoryEvent,
  HistoryEventEntry,
} from '@/modules/history/events/schemas';
import type { HistoryEventDeletePayload, HistoryEventQuestion } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import {
  isEventMissingAccountingRule,
  isEvmEvent,
} from '@/modules/history/event-utils';
import {
  hideDeleteAction,
  hideEditAction,
  shouldDeleteGroup,
} from '@/modules/history/events/event-action-visibility';
import { editTargetFor } from '@/modules/history/events/history-event-edit-target';
import HistoryEventAction from '@/modules/history/events/HistoryEventAction.vue';

const { item, index, completeGroupEvents, unlinkConfirm, collapseAction } = defineProps<{
  item: HistoryEventEntry;
  index: number;
  /**
   * All events in the same group, including hidden and ignored events.
   * This complete set is required for correctly editing grouped events (e.g., swap events).
   */
  completeGroupEvents: HistoryEventEntry[];
  /** Offers unlink in the menu, asking this before `unlink-event` is emitted. */
  unlinkConfirm?: HistoryEventQuestion;
  collapseAction?: boolean;
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'unlink-event': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const COLLAPSE_ACTION_CLASSES = 'w-0 group-hover/row:w-auto 2xl:w-24! 2xl:opacity-0 2xl:group-hover/row:opacity-100 2xl:focus-within:opacity-100';

const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(item));

function editEvent(item: HistoryEvent) {
  emit('edit-event', editTargetFor(item, completeGroupEvents));
}

/**
 * What deleting this row does: a lone EVM event cannot be deleted from its transaction, so the
 * transaction is excluded from accounting instead; a group header removes the whole group.
 */
const deletePayload = computed<HistoryEventDeletePayload>(() => {
  if (isEvmEvent(item) && completeGroupEvents.length === 1)
    return { event: item, type: 'ignore' };

  return {
    ids: shouldDeleteGroup(item, index) ? completeGroupEvents.map(event => event.identifier) : [item.identifier],
    type: 'delete',
  };
});

const deleteConfirm = computed<HistoryEventQuestion | undefined>(() => {
  if (hideDeleteAction(item, index, completeGroupEvents))
    return undefined;

  if (get(deletePayload).type === 'ignore') {
    return {
      confirmLabel: t('transactions.events.confirmation.ignore.action'),
      message: t('transactions.events.confirmation.ignore.message'),
      title: t('transactions.events.confirmation.ignore.title'),
    };
  }

  return {
    confirmLabel: t('common.actions.delete'),
    message: t('transactions.events.confirmation.delete.message'),
    title: t('transactions.events.confirmation.delete.title'),
  };
});
</script>

<template>
  <div
    class="flex items-center gap-1 justify-end"
    :class="{
      'transition-opacity overflow-hidden 2xl:overflow-visible': collapseAction,
      [COLLAPSE_ACTION_CLASSES]: collapseAction && !hasMissingRule,
    }"
  >
    <HistoryEventAction
      :class="{
        'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100 transition-opacity': hasMissingRule && !collapseAction,
        [COLLAPSE_ACTION_CLASSES]: hasMissingRule && collapseAction,
      }"
      :event="item"
      :can-edit="!hideEditAction(item, index)"
      :delete-confirm="deleteConfirm"
      :unlink-confirm="unlinkConfirm"
      @edit="editEvent(item)"
      @delete="emit('delete-event', deletePayload)"
      @unlink="emit('unlink-event')"
    />

    <RuiButton
      v-if="hasMissingRule"
      :title="t('actions.history_events.missing_rule.title')"
      variant="text"
      color="warning"
      icon
      @click="emit('show:missing-rule-action', editTargetFor(item, completeGroupEvents))"
    >
      <RuiIcon
        size="16"
        name="lu-info"
      />
    </RuiButton>
  </div>
</template>
