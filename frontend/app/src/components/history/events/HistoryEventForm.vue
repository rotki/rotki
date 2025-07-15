<script setup lang="ts">
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { kebabCase } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import AssetMovementEventForm from '@/modules/history/management/forms/AssetMovementEventForm.vue';
import EthBlockEventForm from '@/modules/history/management/forms/EthBlockEventForm.vue';
import EthDepositEventForm from '@/modules/history/management/forms/EthDepositEventForm.vue';
import EthWithdrawalEventForm from '@/modules/history/management/forms/EthWithdrawalEventForm.vue';
import EvmEventForm from '@/modules/history/management/forms/EvmEventForm.vue';
import EvmSwapEventForm from '@/modules/history/management/forms/EvmSwapEventForm.vue';
import { EVM_EVENTS, isEvmTypeEvent } from '@/modules/history/management/forms/form-guards';
import OnlineHistoryEventForm from '@/modules/history/management/forms/OnlineHistoryEventForm.vue';
import SwapEventForm from '@/modules/history/management/forms/SwapEventForm.vue';

interface FormComponent {
  save: () => Promise<boolean>;
}

interface HistoryEventFormProps {
  data: GroupEventData | StandaloneEventData;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<HistoryEventFormProps>();

const { t } = useI18n({ useScope: 'global' });
const { data } = toRefs(props);

const entryType = ref<HistoryEventEntryType>(HistoryEventEntryType.HISTORY_EVENT);
const form = useTemplateRef<ComponentPublicInstance<FormComponent>>('form');

const isEvmGroupAdd = computed<boolean>(() => {
  const data = props.data;
  if (data.type !== 'group-add') {
    return false;
  }
  return isEvmTypeEvent(data.group.entryType);
});

const historyEventEntryTypes = computed<HistoryEventEntryType[]>(() => {
  if (get(isEvmGroupAdd)) {
    return [...EVM_EVENTS];
  }
  return Object.values(HistoryEventEntryType).filter(value => !isEvmTypeEvent(value));
});

const formComponents: Record<HistoryEventEntryType, Component> = {
  [HistoryEventEntryType.ASSET_MOVEMENT_EVENT]: AssetMovementEventForm,
  [HistoryEventEntryType.ETH_BLOCK_EVENT]: EthBlockEventForm,
  [HistoryEventEntryType.ETH_DEPOSIT_EVENT]: EthDepositEventForm,
  [HistoryEventEntryType.ETH_WITHDRAWAL_EVENT]: EthWithdrawalEventForm,
  [HistoryEventEntryType.EVM_EVENT]: EvmEventForm,
  [HistoryEventEntryType.EVM_SWAP_EVENT]: EvmSwapEventForm,
  [HistoryEventEntryType.HISTORY_EVENT]: OnlineHistoryEventForm,
  [HistoryEventEntryType.SWAP_EVENT]: SwapEventForm,
};

async function save() {
  if (!isDefined(form))
    return false;

  return await get(form).save();
}

watchImmediate(data, (data) => {
  if (!data) {
    return;
  }
  if (data.type === 'edit')
    set(entryType, data.event.entryType);
  else if (data.type === 'edit-group')
    set(entryType, data.eventsInGroup[0].entryType);
  else if (data.type === 'group-add')
    set(entryType, data.group.entryType);
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
      :disabled="data.type !== 'add' && !isEvmGroupAdd"
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
      :data="data"
    />
  </form>
</template>
