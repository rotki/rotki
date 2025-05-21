<script setup lang="ts">
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';

import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { HistoryEventEntryType } from '@rotki/common';
import { pick } from 'es-toolkit';

const props = defineProps<{
  item: HistoryEventEntry;
  index: number;
  events: HistoryEventEntry[];
  eventGroup: HistoryEventEntry;
  isLast: boolean;
  isHighlighted?: boolean;
  compact?: boolean;
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const { getChain } = useSupportedChains();

function isNoTxHash(item: HistoryEventEntry) {
  return (
    item.entryType === HistoryEventEntryType.EVM_EVENT
    && ((item.counterparty === 'eth2' && item.eventSubtype === 'deposit asset')
      || (item.counterparty === 'gitcoin' && item.eventSubtype === 'apply')
      || item.counterparty === 'safe-multisig')
  );
}

function getNotes(description: string | undefined, notes: string | undefined | null): string | undefined {
  if (description) {
    return notes ? `${description}. ${notes}` : description;
  }
  return notes || undefined;
}

function getEventNoteAttrs(event: HistoryEventEntry) {
  const data: {
    validatorIndex?: number;
    blockNumber?: number;
    counterparty?: string;
    extraData?: Record<string, any>;
  } = {};

  if ('validatorIndex' in event)
    data.validatorIndex = event.validatorIndex;

  if ('blockNumber' in event)
    data.blockNumber = event.blockNumber;
  else if ('blockNumber' in props.eventGroup)
    data.blockNumber = props.eventGroup.blockNumber;

  if ('counterparty' in event && event.counterparty)
    data.counterparty = event.counterparty;

  if ('extraData' in event && event.extraData)
    data.extraData = event.extraData;

  const { asset, autoNotes, userNotes } = pick(event, ['userNotes', 'autoNotes', 'asset']);

  return {
    asset,
    notes: getNotes(autoNotes, userNotes),
    ...data,
  };
}
</script>

<template>
  <LazyLoader
    min-height="5rem"
    class="border-default"
    :class="{
      'bg-rui-error/[0.05]': isHighlighted,
      'border-b': !isLast && !compact,
    }"
  >
    <div
      class="transition-all duration-300 ease-in-out"
      :class="{
        'grid md:grid-cols-10 gap-x-2 gap-y-1 @5xl:!grid-cols-[repeat(20,minmax(0,1fr))] items-center py-3 px-0 md:pl-3': !compact,
        'py-2 md:py-2': compact,
      }"
    >
      <HistoryEventType
        v-if="!compact"
        :event="item"
        :chain="getChain(item.location)"
        class="col-span-10 md:col-span-4 @5xl:!col-span-5 pt-1.5 pb-4 @5xl:py-0"
      />

      <HistoryEventAsset
        :event="item"
        class="transition-all duration-300"
        :class="{
          'col-span-10 md:col-span-6 @5xl:!col-span-4': !compact,
          'w-full !py-0': compact,
        }"
      />

      <HistoryEventNote
        v-if="!compact"
        v-bind="getEventNoteAttrs(item)"
        :amount="item.amount"
        :chain="getChain(item.location)"
        :no-tx-hash="isNoTxHash(item)"
        class="break-words leading-6 col-span-10 @md:col-span-7 @5xl:!col-span-8"
      />

      <HistoryEventsListItemAction
        v-if="!compact"
        class="col-span-10 @md:col-span-3"
        :item="item"
        :index="index"
        :events="events"
        @edit-event="emit('edit-event', $event)"
        @delete-event="emit('delete-event', $event)"
        @show:missing-rule-action="emit('show:missing-rule-action', $event)"
      />
    </div>
  </LazyLoader>
</template>
