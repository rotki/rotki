<script setup lang="ts">
import type {
  LocationAndTxRef,
  PullEventPayload,
} from '@/types/history/events';
import type {
  EthBlockEvent,
  EvmHistoryEvent,
  EvmSwapEvent,
  HistoryEvent,
  HistoryEventEntry,
  SolanaEvent,
  SolanaSwapEvent,
  StandaloneEditableEvents,
} from '@/types/history/events/schemas';
import { DuplicateHandlingStatus } from '@/composables/history/events/types';
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { useReportIssue } from '@/composables/report-issue';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import {
  type DecodableEventType,
  isGroupEditableHistoryEvent,
} from '@/modules/history/management/forms/form-guards';
import {
  isEthBlockEvent,
  isEthBlockEventRef,
  isEvmEvent,
  isEvmSwapEvent,
  isOnlineHistoryEvent,
  isSolanaEvent,
  isSolanaSwapEvent,
  toLocationAndTxRef,
} from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
  loading: boolean;
  duplicateHandlingStatus?: DuplicateHandlingStatus;
}>();

const emit = defineEmits<{
  'add-event': [event: StandaloneEditableEvents];
  'toggle-ignore': [event: HistoryEventEntry];
  'redecode': [event: PullEventPayload];
  'redecode-with-options': [event: PullEventPayload];
  'delete-tx': [data: LocationAndTxRef];
  'fix-duplicate': [];
  'ignore-duplicate': [];
}>();

const {
  ethBlockEventsDecoding,
  txEventsDecoding,
} = useHistoryEventsStatus();

const { confirmAndFixDuplicate, confirmAndMarkNonDuplicated, fixLoading, ignoreLoading } = useCustomizedEventDuplicates();

const { duplicateHandlingStatus, event } = toRefs(props);

const isAutoFixable = computed<boolean>(() => get(duplicateHandlingStatus) === DuplicateHandlingStatus.AUTO_FIX);
const isDuplicate = computed<boolean>(() => !!get(duplicateHandlingStatus) && get(duplicateHandlingStatus) !== DuplicateHandlingStatus.IGNORED);

const showMenu = ref<boolean>(false);

const evmEvent = computed<EvmHistoryEvent | EvmSwapEvent | undefined>(() => {
  const currentEvent = get(event);
  if (isEvmSwapEvent(currentEvent) || isEvmEvent(currentEvent)) {
    return currentEvent;
  }

  return undefined;
});

const solanaEvent = computed<SolanaEvent | SolanaSwapEvent | undefined>(() => {
  const currentEvent = get(event);
  if (isSolanaSwapEvent(currentEvent) || isSolanaEvent(currentEvent)) {
    return currentEvent;
  }

  return undefined;
});

const eventWithDecoding = computed<DecodableEventType | undefined>(() => get(evmEvent) || get(solanaEvent));

const eventWithTxRef = computed<{ location: string; txRef: string } | undefined>(() => {
  const currentEvent = get(event);
  const evm = get(evmEvent);
  const solana = get(solanaEvent);
  if (evm) {
    return {
      location: evm.location,
      txRef: evm.txRef,
    };
  }

  if (solana) {
    return {
      location: solana.location,
      txRef: solana.txRef,
    };
  }

  if (isOnlineHistoryEvent(currentEvent) && 'txRef' in currentEvent && currentEvent.txRef) {
    return {
      location: currentEvent.location,
      txRef: currentEvent.txRef,
    };
  }

  return undefined;
});

const blockEvent = isEthBlockEventRef(event);

const { t } = useI18n({ useScope: 'global' });

function addEvent(event: HistoryEvent) {
  if (isGroupEditableHistoryEvent(event)) {
    return;
  }
  emit('add-event', event);
}
const toggleIgnore = (event: HistoryEventEntry) => emit('toggle-ignore', event);

function redecode(event: EthBlockEvent | DecodableEventType): void {
  if (isEthBlockEvent(event)) {
    emit('redecode', {
      data: [event.blockNumber],
      type: event.entryType,
    });
    return;
  }

  emit('redecode', {
    data: toLocationAndTxRef(event),
    type: event.entryType,
  });
}

function redecodeWithOptions(event: DecodableEventType): void {
  set(showMenu, false);
  emit('redecode-with-options', {
    data: toLocationAndTxRef(event),
    type: event.entryType,
  });
}

function deleteTxAndEvents(params: LocationAndTxRef) {
  return emit('delete-tx', params);
}

function hideAddAction(item: HistoryEvent): boolean {
  return isGroupEditableHistoryEvent(item);
}

const { show: showReportIssue } = useReportIssue();

function openReportDialog(): void {
  const txRef = get(eventWithTxRef)?.txRef;

  const description = [
    t('actions.history_events.report_issue.description_intro'),
    txRef ? t('actions.history_events.report_issue.tx_hash', { hash: txRef }) : '',
    t('actions.history_events.report_issue.location', { location: get(event).location }),
    '',
    t('actions.history_events.report_issue.more_detail'),
    t('actions.history_events.report_issue.placeholder'),
  ].filter(Boolean).join('\n');

  showReportIssue({
    description,
    title: t('actions.history_events.report_issue.title'),
  });
}

function confirmFixDuplicate(): void {
  const groupIdentifier = get(event).groupIdentifier;
  if (!groupIdentifier)
    return;

  confirmAndFixDuplicate([groupIdentifier], () => emit('fix-duplicate'));
}

function confirmIgnoreDuplicate(): void {
  const groupIdentifier = get(event).groupIdentifier;
  if (!groupIdentifier)
    return;

  confirmAndMarkNonDuplicated([groupIdentifier], () => emit('ignore-duplicate'));
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
      :popper="{ placement: 'bottom-end', scroll: false, resize: false }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="!p-2"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            size="20"
          />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton
          v-if="!hideAddAction(event)"
          variant="list"
          @click="addEvent(event)"
        >
          <template #prepend>
            <RuiIcon name="lu-plus" />
          </template>
          {{ t('transactions.actions.add_event_here') }}
        </RuiButton>
        <RuiButton
          variant="list"
          @click="toggleIgnore(event)"
        >
          <template #prepend>
            <RuiIcon :name="event.ignoredInAccounting ? 'lu-eye' : 'lu-eye-off'" />
          </template>
          {{ event.ignoredInAccounting ? t('transactions.unignore') : t('transactions.ignore') }}
        </RuiButton>
        <template v-if="blockEvent">
          <RuiButton
            variant="list"
            :disabled="loading || ethBlockEventsDecoding"
            @click="redecode(blockEvent)"
          >
            <template #prepend>
              <RuiIcon name="lu-rotate-ccw" />
            </template>
            {{ t('transactions.actions.redecode_events') }}
          </RuiButton>
        </template>
        <template v-else-if="eventWithDecoding">
          <RuiButton
            variant="list"
            :class="{ '!py-2': evmEvent }"
            :disabled="loading || txEventsDecoding"
            @click="redecode(eventWithDecoding)"
          >
            <template #prepend>
              <RuiIcon
                name="lu-rotate-ccw"
                class="min-w-[1.375rem]"
                size="20"
              />
            </template>
            {{ t('transactions.actions.redecode_events') }}
            <template #append>
              <RuiTooltip
                v-if="evmEvent"
                :popper="{ placement: 'top', scroll: false, resize: false }"
              >
                <template #activator>
                  <RuiButton
                    icon
                    variant="text"
                    size="sm"
                    class="!p-2"
                    :disabled="loading || txEventsDecoding"
                    @click.stop="redecodeWithOptions(evmEvent)"
                  >
                    <RuiIcon
                      name="lu-settings-2"
                      size="16"
                    />
                  </RuiButton>
                </template>
                {{ t('transactions.actions.redecode_with_options') }}
              </RuiTooltip>
            </template>
          </RuiButton>
        </template>
        <RuiButton
          v-if="eventWithTxRef"
          variant="list"
          color="error"
          :disabled="loading"
          @click="deleteTxAndEvents(eventWithTxRef)"
        >
          <template #prepend>
            <RuiIcon name="lu-trash-2" />
          </template>
          {{ t('transactions.actions.delete_transaction') }}
        </RuiButton>
        <RuiDivider class="my-2" />
        <RuiButton
          variant="list"
          @click="openReportDialog()"
        >
          <template #prepend>
            <RuiIcon name="lu-bug" />
          </template>
          {{ t('actions.history_events.report_issue.action') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
