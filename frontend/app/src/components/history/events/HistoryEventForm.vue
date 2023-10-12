<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type Ref } from 'vue';
import { type HistoryEventEntry } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem: HistoryEventEntry | null;
    nextSequence?: string | null;
    groupHeader: HistoryEventEntry | null;
  }>(),
  {
    nextSequence: null
  }
);

const { groupHeader } = toRefs(props);

const entryType: Ref<HistoryEventEntryType> = ref(
  HistoryEventEntryType.EVM_EVENT
);

const historyEventEntryTypes = Object.values(HistoryEventEntryType);

watchImmediate(groupHeader, groupHeader => {
  if (groupHeader) {
    set(entryType, groupHeader.entryType);
  }
});
</script>

<template>
  <form data-cy="history-event-form" class="history-event-form pt-4">
    <div>
      <VSelect
        v-model="entryType"
        :items="historyEventEntryTypes"
        :disabled="!!groupHeader"
        outlined
        label="Entry Type"
        hide-details
      />
    </div>
    <div class="border-t my-8" />
    <EvmEventForm
      v-if="entryType === HistoryEventEntryType.EVM_EVENT"
      :next-sequence="nextSequence"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <OnlineHistoryEventForm
      v-if="entryType === HistoryEventEntryType.HISTORY_EVENT"
      :next-sequence="nextSequence"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <EthBlockEventForm
      v-if="entryType === HistoryEventEntryType.ETH_BLOCK_EVENT"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <EthDepositEventForm
      v-if="entryType === HistoryEventEntryType.ETH_DEPOSIT_EVENT"
      :next-sequence="nextSequence"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
    <EthWithdrawalEventForm
      v-if="entryType === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT"
      :group-header="groupHeader"
      :editable-item="editableItem"
    />
  </form>
</template>
