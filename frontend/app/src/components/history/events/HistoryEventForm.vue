<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type Ref } from 'vue';
import { type HistoryEventEntry } from '@/types/history/events';
import { toCapitalCase } from '../../../utils/text';

const props = withDefaults(
  defineProps<{
    editableItem?: HistoryEventEntry | null;
    nextSequence?: string | null;
    groupHeader?: HistoryEventEntry | null;
  }>(),
  {
    editableItem: null,
    nextSequence: null,
    groupHeader: null
  }
);

const { groupHeader, editableItem } = toRefs(props);

const entryType: Ref<HistoryEventEntryType> = ref(
  HistoryEventEntryType.HISTORY_EVENT
);

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
  <form class="history-event-form pt-4">
    <div>
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
    </div>

    <RuiDivider class="my-8" />

    <EvmEventForm
      v-if="entryType === HistoryEventEntryType.EVM_EVENT"
      data-cy="evm-event-form"
      :next-sequence="nextSequence"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <OnlineHistoryEventForm
      v-if="entryType === HistoryEventEntryType.HISTORY_EVENT"
      data-cy="history-event-form"
      :next-sequence="nextSequence"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <EthBlockEventForm
      v-if="entryType === HistoryEventEntryType.ETH_BLOCK_EVENT"
      data-cy="eth-block-event-form"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <EthDepositEventForm
      v-if="entryType === HistoryEventEntryType.ETH_DEPOSIT_EVENT"
      data-cy="eth-deposit-event-form"
      :next-sequence="nextSequence"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <EthWithdrawalEventForm
      v-if="entryType === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT"
      data-cy="eth-withdrawal-event-form"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
  </form>
</template>
