<script setup lang="ts">
import type { EventData } from '@/types/history/events';
import AssetMovementEventForm from '@/components/history/events/forms/AssetMovementEventForm.vue';
import EthBlockEventForm from '@/components/history/events/forms/EthBlockEventForm.vue';
import EthDepositEventForm from '@/components/history/events/forms/EthDepositEventForm.vue';
import EthWithdrawalEventForm from '@/components/history/events/forms/EthWithdrawalEventForm.vue';
import EvmEventForm from '@/components/history/events/forms/EvmEventForm.vue';
import OnlineHistoryEventForm from '@/components/history/events/forms/OnlineHistoryEventForm.vue';
import SwapEventForm from '@/modules/history/management/forms/SwapEventForm.vue';
import { HistoryEventEntryType } from '@rotki/common';
import { kebabCase } from 'es-toolkit';
import { useTemplateRef } from 'vue';

interface FormComponent {
  save: () => Promise<boolean>;
}

interface HistoryEventFormProps {
  data?: EventData;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = withDefaults(defineProps<HistoryEventFormProps>(), {
  data: undefined,
});

const { t } = useI18n();
const { data } = toRefs(props);

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
  if (data.event)
    set(entryType, data.event.entryType);
  else if (data.group)
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
      :disabled="!!data?.group"
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
