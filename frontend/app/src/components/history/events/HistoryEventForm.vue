<script setup lang="ts">
import type { HistoryEvent } from '@/types/history/events';
import AssetMovementEventForm from '@/components/history/events/forms/AssetMovementEventForm.vue';
import EthBlockEventForm from '@/components/history/events/forms/EthBlockEventForm.vue';
import EthDepositEventForm from '@/components/history/events/forms/EthDepositEventForm.vue';
import EthWithdrawalEventForm from '@/components/history/events/forms/EthWithdrawalEventForm.vue';
import EvmEventForm from '@/components/history/events/forms/EvmEventForm.vue';
import OnlineHistoryEventForm from '@/components/history/events/forms/OnlineHistoryEventForm.vue';
import { isOfEventType } from '@/utils/history/events';
import { HistoryEventEntryType } from '@rotki/common';
import { kebabCase } from 'es-toolkit';
import { useTemplateRef } from 'vue';

interface FormComponent {
  save: () => Promise<boolean>;
}

interface HistoryEventFormProps {
  editableItem?: HistoryEvent;
  nextSequence?: string;
  groupHeader?: HistoryEvent;
  groupEvents?: HistoryEvent[];
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = withDefaults(defineProps<HistoryEventFormProps>(), {
  editableItem: undefined,
  groupEvents: undefined,
  groupHeader: undefined,
  nextSequence: undefined,
});

const { t } = useI18n();
const { editableItem, groupHeader } = toRefs(props);

const entryType = ref<HistoryEventEntryType>(HistoryEventEntryType.HISTORY_EVENT);
const form = useTemplateRef<ComponentPublicInstance<FormComponent>>('form');
const historyEventEntryTypes = Object.values(HistoryEventEntryType);

const formComponents: Record<HistoryEventEntryType, Component> = {
  [HistoryEventEntryType.ASSET_MOVEMENT_EVENT]: AssetMovementEventForm,
  [HistoryEventEntryType.ETH_BLOCK_EVENT]: EthBlockEventForm,
  [HistoryEventEntryType.ETH_DEPOSIT_EVENT]: EthDepositEventForm,
  [HistoryEventEntryType.ETH_WITHDRAWAL_EVENT]: EthWithdrawalEventForm,
  [HistoryEventEntryType.EVM_EVENT]: EvmEventForm,
  [HistoryEventEntryType.HISTORY_EVENT]: OnlineHistoryEventForm,
};

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

async function save() {
  if (!isDefined(form))
    return false;

  return await get(form).save();
}

watchImmediate([groupHeader, editableItem], ([groupHeader, editableItem]) => {
  if (editableItem)
    set(entryType, editableItem.entryType);
  else if (groupHeader)
    set(entryType, groupHeader.entryType);
});

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

    <Component
      :is="formComponents[entryType]"
      ref="form"
      v-model:state-updated="stateUpdated"
      :data-cy="`${kebabCase(entryType)}-form`"
      :next-sequence="nextSequence"
      :group-header="getEvent(groupHeader, entryType)"
      :editable-item="getEvent(editableItem, entryType)"
      :group-events="entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT
        ? getEvents(groupEvents, entryType)
        : undefined"
    />
  </form>
</template>
