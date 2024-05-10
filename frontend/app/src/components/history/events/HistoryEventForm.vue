<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import type { HistoryEvent } from '@/types/history/events';

const props = withDefaults(
  defineProps<{
    editableItem?: HistoryEvent;
    nextSequence?: string;
    groupHeader?: HistoryEvent;
  }>(),
  {
    editableItem: undefined,
    nextSequence: undefined,
    groupHeader: undefined,
  },
);

const { t } = useI18n();
const { groupHeader, editableItem } = toRefs(props);

const entryType: Ref<HistoryEventEntryType> = ref(
  HistoryEventEntryType.HISTORY_EVENT,
);

function getEvent<T extends HistoryEvent>(event: HistoryEvent, type: HistoryEventEntryType): T | undefined {
  if (isOfEventType<T>(event, type))
    return event;

  return undefined;
}

const historyEventEntryTypes = Object.values(HistoryEventEntryType);

watchImmediate([groupHeader, editableItem], ([groupHeader, editableItem]) => {
  if (editableItem)
    set(entryType, editableItem.entryType);
  else if (groupHeader)
    set(entryType, groupHeader.entryType);
});
</script>

<template>
  <form class="history-event-form">
    <RuiMenuSelect
      v-model="entryType"
      data-cy="entry-type"
      :options="historyEventEntryTypes"
      :disabled="!!groupHeader"
      :label="t('common.entry_type')"
      key-attr="key"
      full-width
      variant="outlined"
    >
      <template #activator.text="{ value }">
        <span class="capitalize">
          {{ value.key }}
        </span>
      </template>
      <template #item.text="{ option }">
        <span class="capitalize">
          {{ option.key }}
        </span>
      </template>
    </RuiMenuSelect>

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
