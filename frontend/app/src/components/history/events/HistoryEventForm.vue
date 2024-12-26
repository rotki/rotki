<script setup lang="ts">
import { HistoryEventEntryType } from '@rotki/common';
import { useTemplateRef } from 'vue';
import { isOfEventType } from '@/utils/history/events';
import EthWithdrawalEventForm from '@/components/history/events/forms/EthWithdrawalEventForm.vue';
import EthDepositEventForm from '@/components/history/events/forms/EthDepositEventForm.vue';
import EthBlockEventForm from '@/components/history/events/forms/EthBlockEventForm.vue';
import OnlineHistoryEventForm from '@/components/history/events/forms/OnlineHistoryEventForm.vue';
import EvmEventForm from '@/components/history/events/forms/EvmEventForm.vue';
import AssetMovementEventForm from '@/components/history/events/forms/AssetMovementEventForm.vue';
import type { HistoryEvent } from '@/types/history/events';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = withDefaults(defineProps<{
  editableItem?: HistoryEvent;
  nextSequence?: string;
  groupHeader?: HistoryEvent;
  groupEvents?: HistoryEvent[];
}>(), {
  editableItem: undefined,
  groupEvents: undefined,
  groupHeader: undefined,
  nextSequence: undefined,
});

const { t } = useI18n();
const { editableItem, groupHeader } = toRefs(props);

const entryType = ref<HistoryEventEntryType>(HistoryEventEntryType.HISTORY_EVENT);
const form = useTemplateRef<InstanceType<typeof EvmEventForm | typeof OnlineHistoryEventForm | typeof EthBlockEventForm | typeof EthDepositEventForm | typeof EthWithdrawalEventForm | typeof AssetMovementEventForm>>('form');

function getEvent<T extends HistoryEvent>(event: HistoryEvent | undefined, type: HistoryEventEntryType): T | undefined {
  if (event && isOfEventType<T>(event, type))
    return event;

  return undefined;
}

function getEvents<T extends HistoryEvent>(events: HistoryEvent[] | undefined, type: HistoryEventEntryType): T[] | undefined {
  if (!events)
    return undefined;

  return events.filter((event): event is T => isOfEventType<T>(event, type));
}

const historyEventEntryTypes = Object.values(HistoryEventEntryType);

watchImmediate([groupHeader, editableItem], ([groupHeader, editableItem]) => {
  if (editableItem)
    set(entryType, editableItem.entryType);
  else if (groupHeader)
    set(entryType, groupHeader.entryType);
});

async function save() {
  const formVal = get(form);

  if (!formVal)
    return false;

  return await formVal.save();
}

defineExpose({
  save,
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
      hide-details
      variant="outlined"
    >
      <template #selection="{ item }">
        <span class="capitalize">
          {{ item }}
        </span>
      </template>
      <template #item="{ item }">
        <span class="capitalize">
          {{ item }}
        </span>
      </template>
    </RuiMenuSelect>

    <RuiDivider class="my-8" />

    <EvmEventForm
      v-if="entryType === HistoryEventEntryType.EVM_EVENT"
      ref="form"
      v-model:state-updated="stateUpdated"
      data-cy="evm-event-form"
      :next-sequence="nextSequence"
      :group-header="getEvent(groupHeader, HistoryEventEntryType.EVM_EVENT)"
      :editable-item="getEvent(editableItem, HistoryEventEntryType.EVM_EVENT)"
    />
    <OnlineHistoryEventForm
      v-if="entryType === HistoryEventEntryType.HISTORY_EVENT"
      ref="form"
      v-model:state-updated="stateUpdated"

      data-cy="history-event-form"
      :next-sequence="nextSequence"
      :group-header="getEvent(groupHeader, HistoryEventEntryType.HISTORY_EVENT)"
      :editable-item="getEvent(editableItem, HistoryEventEntryType.HISTORY_EVENT)"
    />
    <EthBlockEventForm
      v-if="entryType === HistoryEventEntryType.ETH_BLOCK_EVENT"
      ref="form"
      v-model:state-updated="stateUpdated"
      data-cy="eth-block-event-form"
      :group-header="getEvent(groupHeader, HistoryEventEntryType.ETH_BLOCK_EVENT)"
      :editable-item="getEvent(editableItem, HistoryEventEntryType.ETH_BLOCK_EVENT)"
    />
    <EthDepositEventForm
      v-if="entryType === HistoryEventEntryType.ETH_DEPOSIT_EVENT"
      ref="form"
      v-model:state-updated="stateUpdated"
      data-cy="eth-deposit-event-form"
      :next-sequence="nextSequence"
      :group-header="getEvent(groupHeader, HistoryEventEntryType.ETH_DEPOSIT_EVENT)"
      :editable-item="getEvent(editableItem, HistoryEventEntryType.ETH_DEPOSIT_EVENT)"
    />
    <EthWithdrawalEventForm
      v-if="entryType === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT"
      ref="form"
      v-model:state-updated="stateUpdated"
      data-cy="eth-withdrawal-event-form"
      :group-header="getEvent(groupHeader, HistoryEventEntryType.ETH_WITHDRAWAL_EVENT)"
      :editable-item="getEvent(editableItem, HistoryEventEntryType.ETH_WITHDRAWAL_EVENT)"
    />
    <AssetMovementEventForm
      v-if="entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT"
      ref="form"
      v-model:state-updated="stateUpdated"
      data-cy="asset-movement-event-form"
      :group-events="getEvents(groupEvents, HistoryEventEntryType.ASSET_MOVEMENT_EVENT)"
      :editable-item="getEvent(editableItem, HistoryEventEntryType.ASSET_MOVEMENT_EVENT)"
    />
  </form>
</template>
