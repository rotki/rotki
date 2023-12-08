<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type Ref } from 'vue';
import { toCapitalCase } from '@/utils/text';
import { type HistoryEvent } from '@/types/history/events';
import { isOfEventType } from '@/utils/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: HistoryEvent;
    nextSequence?: string;
    groupHeader?: HistoryEvent;
  }>(),
  {
    editableItem: undefined,
    nextSequence: undefined,
    groupHeader: undefined
  }
);

const { groupHeader, editableItem } = toRefs(props);

const entryType: Ref<HistoryEventEntryType> = ref(
  HistoryEventEntryType.HISTORY_EVENT
);

const getEvent = <T extends HistoryEvent>(
  event: HistoryEvent,
  type: HistoryEventEntryType
): T | undefined => {
  if (isOfEventType<T>(event, type)) {
    return event;
  }
  return undefined;
};

const historyEventEntryTypes = Object.values(HistoryEventEntryType);

watchImmediate([groupHeader, editableItem], ([groupHeader, editableItem]) => {
  if (editableItem) {
    set(entryType, editableItem.entryType);
  } else if (groupHeader) {
    set(entryType, groupHeader.entryType);
  }
});
</script>

<template>
  <form class="history-event-form">
    <VSelect
      v-model="entryType"
      data-cy="entry-type"
      :items="historyEventEntryTypes"
      :disabled="!!groupHeader"
      outlined
      label="Entry Type"
      hide-details
    >
      <template #item="{ item }">{{ toCapitalCase(item) }}</template>
      <template #selection="{ item }">{{ toCapitalCase(item) }}</template>
    </VSelect>

    <RuiDivider class="my-8" />

    <EvmEventForm
      v-if="entryType === HistoryEventEntryType.EVM_EVENT"
      data-cy="evm-event-form"
      :next-sequence="nextSequence"
      :group-header="getEvent(groupHeader, HistoryEventEntryType.EVM_EVENT)"
      :editable-item="getEvent(editableItem, HistoryEventEntryType.EVM_EVENT)"
    />
    <OnlineHistoryEventForm
      v-if="entryType === HistoryEventEntryType.HISTORY_EVENT"
      data-cy="history-event-form"
      :next-sequence="nextSequence"
      :group-header="getEvent(groupHeader, HistoryEventEntryType.HISTORY_EVENT)"
      :editable-item="
        getEvent(editableItem, HistoryEventEntryType.HISTORY_EVENT)
      "
    />
    <EthBlockEventForm
      v-if="entryType === HistoryEventEntryType.ETH_BLOCK_EVENT"
      data-cy="eth-block-event-form"
      :group-header="
        getEvent(groupHeader, HistoryEventEntryType.ETH_BLOCK_EVENT)
      "
      :editable-item="
        getEvent(editableItem, HistoryEventEntryType.ETH_BLOCK_EVENT)
      "
    />
    <EthDepositEventForm
      v-if="entryType === HistoryEventEntryType.ETH_DEPOSIT_EVENT"
      data-cy="eth-deposit-event-form"
      :next-sequence="nextSequence"
      :group-header="
        getEvent(groupHeader, HistoryEventEntryType.ETH_DEPOSIT_EVENT)
      "
      :editable-item="
        getEvent(editableItem, HistoryEventEntryType.ETH_DEPOSIT_EVENT)
      "
    />
    <EthWithdrawalEventForm
      v-if="entryType === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT"
      data-cy="eth-withdrawal-event-form"
      :group-header="
        getEvent(groupHeader, HistoryEventEntryType.ETH_WITHDRAWAL_EVENT)
      "
      :editable-item="
        getEvent(editableItem, HistoryEventEntryType.ETH_WITHDRAWAL_EVENT)
      "
    />
  </form>
</template>
