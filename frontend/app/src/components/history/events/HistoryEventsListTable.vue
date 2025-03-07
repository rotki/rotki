<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import RowActions from '@/components/helper/RowActions.vue';
import HistoryEventAction from '@/components/history/events/HistoryEventAction.vue';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { useSupportedChains } from '@/composables/info/chains';
import {
  isAssetMovementEvent,
  isEventAccountingRuleProcessed,
  isEventMissingAccountingRule,
  isEvmEvent,
} from '@/utils/history/events';
import { HistoryEventEntryType } from '@rotki/common';
import { pick } from 'es-toolkit';

interface DeleteEvent {
  canDelete: boolean;
  item: HistoryEventEntry;
}

const props = withDefaults(
  defineProps<{
    events: HistoryEventEntry[];
    eventGroup: HistoryEventEntry;
    loading?: boolean;
    total?: number;
    highlightedIdentifiers?: string[];
  }>(),
  {
    loading: false,
    total: 0,
  },
);

const emit = defineEmits<{
  (e: 'edit-event', data: HistoryEventEntry): void;
  (e: 'delete-event', data: DeleteEvent): void;
  (e: 'show:missing-rule-action', data: HistoryEventEntry): void;
}>();

const { t } = useI18n();
const { getChain } = useSupportedChains();

function isNoTxHash(item: HistoryEventEntry) {
  return (
    item.entryType === HistoryEventEntryType.EVM_EVENT
    && ((item.counterparty === 'eth2' && item.eventSubtype === 'deposit asset')
      || (item.counterparty === 'gitcoin' && item.eventSubtype === 'apply')
      || item.counterparty === 'safe-multisig')
  );
}

const editEvent = (item: HistoryEventEntry) => emit('edit-event', item);

function deleteEvent(item: HistoryEventEntry) {
  return emit('delete-event', {
    canDelete: isEvmEvent(item) ? props.events.length > 1 : true,
    item,
  });
}

function getEventNoteAttrs(event: HistoryEventEntry) {
  const data: {
    validatorIndex?: number;
    blockNumber?: number;
    counterparty?: string;
  } = {};

  if ('validatorIndex' in event)
    data.validatorIndex = event.validatorIndex;

  if ('blockNumber' in event)
    data.blockNumber = event.blockNumber;
  else if ('blockNumber' in props.eventGroup)
    data.blockNumber = props.eventGroup.blockNumber;

  if ('counterparty' in event && event.counterparty)
    data.counterparty = event.counterparty;

  // todo: validate optional or nullable state of schema
  const { asset, notes } = pick(event, ['notes', 'asset']);

  return {
    asset,
    notes: notes || undefined,
    ...data,
  };
}

function hideEventAction(item: HistoryEventEntry): boolean {
  return isAssetMovementEvent(item) && item.eventSubtype === 'fee';
}
</script>

<template>
  <div>
    <template v-if="total > 0">
      <LazyLoader
        v-for="(item, index) in events"
        :key="item.identifier"
        min-height="5rem"
        class="grid md:grid-cols-4 gap-x-2 gap-y-4 lg:grid-cols-[repeat(20,minmax(0,1fr))] py-3 items-center -mx-4 px-4"
        :class="{
          'border-b border-default': index < events.length - 1,
          'bg-rui-error/[0.05]': highlightedIdentifiers && highlightedIdentifiers.includes(item.identifier.toString()),
        }"
      >
        <HistoryEventType
          :event="item"
          :chain="getChain(item.location)"
          class="md:col-span-2 lg:col-span-6"
        />
        <HistoryEventAsset
          :event="item"
          class="md:col-span-2 lg:col-span-4"
        />
        <HistoryEventNote
          v-bind="getEventNoteAttrs(item)"
          :amount="item.amount"
          :chain="getChain(item.location)"
          :no-tx-hash="isNoTxHash(item)"
          class="break-words leading-6 md:col-span-3 lg:col-span-7"
        />
        <RowActions
          class="lg:col-span-3"
          align="end"
          :delete-tooltip="t('transactions.events.actions.delete')"
          :edit-tooltip="t('transactions.events.actions.edit')"
          :no-delete="hideEventAction(item)"
          :no-edit="hideEventAction(item)"
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
                @click="emit('show:missing-rule-action', item)"
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
      </LazyLoader>
    </template>

    <template v-else>
      <div v-if="loading">
        {{ t('transactions.events.loading') }}
      </div>
      <div v-else>
        {{ t('transactions.events.no_data') }}
      </div>
    </template>
  </div>
</template>
