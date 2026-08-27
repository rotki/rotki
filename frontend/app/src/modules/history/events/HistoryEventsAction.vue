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
import RedecodeEventsButton from '@/modules/history/events/RedecodeEventsButton.vue';
import { useHistoryEventActionMenu } from '@/modules/history/events/use-history-event-action-menu';
import { type DecodableEventType, isGroupEditableHistoryEvent } from '@/modules/history/management/forms/form-guards';

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

const {
  blockEvent,
  canAddEvent,
  canDeleteEvents,
  confirmFixDuplicate,
  confirmIgnoreDuplicate,
  decodableEvmEvent,
  deletableEventIds,
  ethBlockEventsDecoding,
  eventWithDecoding,
  eventWithTxRef,
  fixLoading,
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
  // `canAddEvent` already hides the action for a group-editable event; this narrows the
  // row to the shape the event carries.
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
</script>

<template>
  <div class="flex items-center">
    <RuiButton
      v-if="isAutoFixable"
      size="sm"
      color="primary"
      class="mr-1"
      :loading="fixLoading"
      data-testid="event-fix-duplicate"
      @click="confirmFixDuplicate()"
    >
      <template #prepend>
        <RuiIcon
          name="lu-wand-sparkles"
          size="16"
        />
      </template>
      {{ t('customized_event_duplicates.actions.fix') }}
    </RuiButton>
    <RuiButton
      v-if="isDuplicate"
      variant="outlined"
      size="sm"
      class="mr-2"
      :loading="ignoreLoading"
      data-testid="event-ignore-duplicate"
      @click="confirmIgnoreDuplicate()"
    >
      <template #prepend>
        <RuiIcon
          name="lu-eye-off"
          size="16"
        />
      </template>
      {{ t('customized_event_duplicates.actions.mark_non_duplicated') }}
    </RuiButton>
    <RuiMenu
      v-model="showMenu"
      menu-class="max-w-[15rem] z-[100]"
      :options="{ autoUpdate: { resize: false, scroll: false }, placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="!p-2"
          data-testid="event-actions-menu"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            size="20"
          />
        </RuiButton>
      </template>
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
        @click="emit('delete-tx', eventWithTxRef)"
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
        @click="emit('delete-events', deletableEventIds())"
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
    </RuiMenu>
  </div>
</template>
