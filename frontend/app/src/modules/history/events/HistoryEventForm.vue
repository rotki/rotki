<script setup lang="ts">
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { kebabCase } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import AssetMovementEventForm from '@/modules/history/management/forms/AssetMovementEventForm.vue';
import BitcoinEventForm from '@/modules/history/management/forms/BitcoinEventForm.vue';
import EthBlockEventForm from '@/modules/history/management/forms/EthBlockEventForm.vue';
import EthDepositEventForm from '@/modules/history/management/forms/EthDepositEventForm.vue';
import EthWithdrawalEventForm from '@/modules/history/management/forms/EthWithdrawalEventForm.vue';
import EvmEventForm from '@/modules/history/management/forms/EvmEventForm.vue';
import OnlineHistoryEventForm from '@/modules/history/management/forms/OnlineHistoryEventForm.vue';
import SolanaEventForm from '@/modules/history/management/forms/SolanaEventForm.vue';
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
  [HistoryEventEntryType.BANK_TRANSACTION_EVENT]: OnlineHistoryEventForm,
  [HistoryEventEntryType.BITCOIN_EVENT]: BitcoinEventForm,
  [HistoryEventEntryType.ETH_BLOCK_EVENT]: EthBlockEventForm,
  [HistoryEventEntryType.ETH_DEPOSIT_EVENT]: EthDepositEventForm,
  [HistoryEventEntryType.ETH_WITHDRAWAL_EVENT]: EthWithdrawalEventForm,
  [HistoryEventEntryType.EVM_EVENT]: EvmEventForm,
  [HistoryEventEntryType.EVM_SWAP_EVENT]: SwapEventForm,
  [HistoryEventEntryType.HISTORY_EVENT]: OnlineHistoryEventForm,
  [HistoryEventEntryType.SOLANA_EVENT]: SolanaEventForm,
  [HistoryEventEntryType.SOLANA_SWAP_EVENT]: SwapEventForm,
  [HistoryEventEntryType.SWAP_EVENT]: SwapEventForm,
};

/** Forms that serve several entry types, and so are told which one is picked. */
const formsOfSeveralTypes = new Set<Component>([OnlineHistoryEventForm, SwapEventForm]);

const formEntryType = computed<HistoryEventEntryType | undefined>(() =>
  (formsOfSeveralTypes.has(formComponents[entryType]) ? entryType : undefined));

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
