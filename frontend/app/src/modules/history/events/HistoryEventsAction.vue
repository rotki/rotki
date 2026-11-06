<script setup lang="ts">
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type {
  LocationAndTxRef,
  PullEventPayload,
} from '@/modules/history/events/event-payloads';
import type {
  HistoryEventEntry,
  StandaloneEditableEvents,
} from '@/modules/history/events/schemas';
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import { startPromise } from '@shared/utils';
import HistoryEventDuplicateActions from '@/modules/history/events/HistoryEventDuplicateActions.vue';
import RedecodeEventsButton from '@/modules/history/events/RedecodeEventsButton.vue';
import { useHistoryEventActionMenu } from '@/modules/history/events/use-history-event-action-menu';
import { type DecodableEventType, isGroupEditableHistoryEvent } from '@/modules/history/management/forms/form-guards';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

const { event, loading, redecoding, duplicateHandlingStatus, groupEvents } = defineProps<{
  event: HistoryEventEntry;
  groupEvents?: HistoryEventEntry[];
  loading: boolean;
  /**
   * This group's own re-decode is in flight. Kept apart from `loading`, which follows every events
   * fetch (paging, scrolling, filtering) and so would disable the action on routine refreshes.
   */
  redecoding?: boolean;
  duplicateHandlingStatus?: DuplicateHandlingStatus;
}>();

const emit = defineEmits<{
  'add-event': [event: StandaloneEditableEvents];
  'toggle-ignore': [event: HistoryEventEntry];
  'redecode': [event: PullEventPayload];
  'redecode-with-options': [event: PullEventPayload];
  'delete-tx': [data: LocationAndTxRef];
  'delete-events': [ids: number[]];
  'fix-duplicate': [];
  'ignore-duplicate': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const showMenu = ref<boolean>(false);
/** The delete the menu is asking about in place of its list, until it is answered or closed. */
const pendingDelete = ref<'transaction' | 'events'>();

const {
  blockEvent,
  canAddEvent,
  canDeleteEvents,
  decodableEvmEvent,
  deletableEventIds,
  ethBlockEventsDecoding,
  eventWithDecoding,
  eventWithTxRef,
  fixDuplicate,
  fixLoading,
  ignoreDuplicate,
  ignoreLoading,
  isAutoFixable,
  isDuplicate,
  openReportDialog,
  toRedecodePayload,
  txEventsDecoding,
} = useHistoryEventActionMenu({
  duplicateHandlingStatus: () => duplicateHandlingStatus,
  event: () => event,
  groupEvents: () => groupEvents,
  onFixDuplicate: () => emit('fix-duplicate'),
  onIgnoreDuplicate: () => emit('ignore-duplicate'),
});

function addEvent(): void {
  if (isGroupEditableHistoryEvent(event))
    return;

  emit('add-event', event);
}

function redecode(target: DecodableEventType): void {
  emit('redecode', toRedecodePayload(target));
}

function redecodeWithOptions(target: DecodableEventType): void {
  set(showMenu, false);
  emit('redecode-with-options', toRedecodePayload(target));
}

const deleteQuestion = computed<HistoryEventQuestion | undefined>(() => {
  const pending = get(pendingDelete);
  if (pending === 'transaction') {
    return {
      message: t('transactions.dialog.delete.message'),
      title: t('transactions.dialog.delete.title'),
    };
  }
  if (pending === 'events') {
    return {
      message: t('transactions.events.confirmation.delete.message'),
      title: t('transactions.events.confirmation.delete.title'),
    };
  }
  return undefined;
});

function acceptDelete(): void {
  const pending = get(pendingDelete);
  const txRef = get(eventWithTxRef);
  set(showMenu, false);
  if (pending === 'transaction' && txRef)
    emit('delete-tx', txRef);
  else if (pending === 'events')
    emit('delete-events', deletableEventIds());
}

watch(showMenu, (open) => {
  if (!open)
    set(pendingDelete, undefined);
});
</script>

<template>
  <div class="flex items-center">
    <HistoryEventDuplicateActions
      :is-auto-fixable="isAutoFixable"
      :is-duplicate="isDuplicate"
      :fix-loading="fixLoading"
      :ignore-loading="ignoreLoading"
      @fix="startPromise(fixDuplicate())"
      @ignore="startPromise(ignoreDuplicate())"
    />
    <RuiMenu
      v-model="showMenu"
      lazy
      :role="deleteQuestion ? 'dialog' : undefined"
      :class-names="{ menu: deleteQuestion ? 'w-72' : 'max-w-60' }"
      :options="{ autoUpdate: { resize: false, scroll: false }, placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="p-2!"
          data-testid="event-actions-menu"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            size="20"
          />
        </RuiButton>
      </template>
      <InlineConfirm
        v-if="deleteQuestion"
        layout="panel"
        tone="error"
        :title="deleteQuestion.title"
        :message="deleteQuestion.message"
        :confirm-label="t('common.actions.delete')"
        @cancel="showMenu = false"
        @confirm="acceptDelete()"
      />
      <template v-else>
        <RuiButton
          v-if="canAddEvent"
          variant="list"
          data-testid="event-add"
          @click="addEvent()"
        >
          <template #prepend>
            <RuiIcon name="lu-plus" />
          </template>
          {{ t('transactions.actions.add_event_here') }}
        </RuiButton>
        <RuiButton
          variant="list"
          data-testid="event-toggle-ignore"
          @click="emit('toggle-ignore', event)"
        >
          <template #prepend>
            <RuiIcon :name="event.ignoredInAccounting ? 'lu-eye' : 'lu-eye-off'" />
          </template>
          {{ event.ignoredInAccounting ? t('transactions.unignore') : t('transactions.ignore') }}
        </RuiButton>
        <template v-if="blockEvent">
          <RuiButton
            variant="list"
            :disabled="loading || redecoding || ethBlockEventsDecoding"
            data-testid="event-redecode-block"
            @click="emit('redecode', toRedecodePayload(blockEvent))"
          >
            <template #prepend>
              <RuiIcon name="lu-rotate-ccw" />
            </template>
            {{ t('transactions.actions.redecode_events') }}
          </RuiButton>
        </template>
        <template v-else-if="eventWithDecoding">
          <RedecodeEventsButton
            :disabled="loading || redecoding || txEventsDecoding"
            :has-options="!!decodableEvmEvent"
            @redecode="redecode(eventWithDecoding)"
            @redecode-with-options="decodableEvmEvent && redecodeWithOptions(decodableEvmEvent)"
          />
        </template>
        <RuiButton
          v-if="eventWithTxRef"
          variant="list"
          color="error"
          :disabled="loading"
          data-testid="event-delete-tx"
          @click.stop="pendingDelete = 'transaction'"
        >
          <template #prepend>
            <RuiIcon name="lu-trash-2" />
          </template>
          {{ t('transactions.actions.delete_transaction') }}
        </RuiButton>
        <RuiButton
          v-else-if="canDeleteEvents"
          variant="list"
          color="error"
          :disabled="loading"
          data-testid="event-delete-events"
          @click.stop="pendingDelete = 'events'"
        >
          <template #prepend>
            <RuiIcon name="lu-trash-2" />
          </template>
          {{ t('transactions.actions.delete_event') }}
        </RuiButton>
        <RuiDivider class="my-2" />
        <RuiButton
          variant="list"
          data-testid="event-report-issue"
          @click="openReportDialog()"
        >
          <template #prepend>
            <RuiIcon name="lu-bug" />
          </template>
          {{ t('actions.history_events.report_issue.action') }}
        </RuiButton>
      </template>
    </RuiMenu>
  </div>
</template>
