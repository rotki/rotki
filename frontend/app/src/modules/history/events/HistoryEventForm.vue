<script setup lang="ts">
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { kebabCase } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import AssetMovementEventForm from '@/modules/history/management/forms/AssetMovementEventForm.vue';
import EthBlockEventForm from '@/modules/history/management/forms/EthBlockEventForm.vue';
import EthDepositEventForm from '@/modules/history/management/forms/EthDepositEventForm.vue';
import EthWithdrawalEventForm from '@/modules/history/management/forms/EthWithdrawalEventForm.vue';
import HistoryEventEntryForm from '@/modules/history/management/forms/HistoryEventEntryForm.vue';
import SwapEventForm from '@/modules/history/management/forms/SwapEventForm.vue';

/** The seam every entry-type form is driven through. */
interface FormComponent {
  save: () => Promise<boolean>;
  errorCount: number;
}

interface HistoryEventFormProps {
  data: GroupEventData | StandaloneEventData;
  /** Picked in the dialog header, which keeps the picker in place while the form below it changes. */
  entryType: HistoryEventEntryType;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data, entryType } = defineProps<HistoryEventFormProps>();

const form = useTemplateRef<ComponentPublicInstance<FormComponent>>('form');

const formComponents: Record<HistoryEventEntryType, Component> = {
  [HistoryEventEntryType.ASSET_MOVEMENT_EVENT]: AssetMovementEventForm,
  [HistoryEventEntryType.BANK_TRANSACTION_EVENT]: HistoryEventEntryForm,
  [HistoryEventEntryType.BITCOIN_EVENT]: HistoryEventEntryForm,
  [HistoryEventEntryType.ETH_BLOCK_EVENT]: EthBlockEventForm,
  [HistoryEventEntryType.ETH_DEPOSIT_EVENT]: EthDepositEventForm,
  [HistoryEventEntryType.ETH_WITHDRAWAL_EVENT]: EthWithdrawalEventForm,
  [HistoryEventEntryType.EVM_EVENT]: HistoryEventEntryForm,
  [HistoryEventEntryType.EVM_SWAP_EVENT]: SwapEventForm,
  [HistoryEventEntryType.HISTORY_EVENT]: HistoryEventEntryForm,
  [HistoryEventEntryType.SOLANA_EVENT]: HistoryEventEntryForm,
  [HistoryEventEntryType.SOLANA_SWAP_EVENT]: SwapEventForm,
  [HistoryEventEntryType.SWAP_EVENT]: SwapEventForm,
};

/**
 * The entry type for the event form, which a new bank transaction keeps. The event and swap forms
 * both serve several types, but otherwise take their kind from the location, the event or the
 * transaction.
 */
const formEntryType = computed<HistoryEventEntryType | undefined>(() =>
  (formComponents[entryType] === HistoryEventEntryForm ? entryType : undefined));

const errorCount = computed<number>(() => {
  const formRef = get(form);
  if (!formRef)
    return 0;
  return formRef.errorCount;
});

async function save() {
  if (!isDefined(form))
    return false;

  return await get(form).save();
}

defineExpose({
  errorCount,
  save,
});
</script>

<template>
  <Component
    :is="formComponents[entryType]"
    ref="form"
    v-model:state-updated="stateUpdated"
    data-testid="event-form"
    :data-key="kebabCase(entryType)"
    :data="data"
    :entry-type="formEntryType"
  />
</template>
