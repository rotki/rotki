<script lang="ts" setup>
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { RepullingTransactionResult } from '@/modules/history/events/tx/use-history-transactions';
import { useTemplateRef } from 'vue';
import RepullingTransactionForm from '@/modules/history/events/tx/RepullingTransactionForm.vue';
import { useRepullingTransactionSubmission } from '@/modules/history/events/tx/use-repulling-transaction-submission';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

const modelValue = defineModel<boolean>({ required: true });

const { repullExchangeEvents, repullTransactions } = defineProps<{
  loading?: boolean;
  repullTransactions?: (result: RepullingTransactionResult) => void;
  repullExchangeEvents?: (exchanges: Exchange[]) => void;
}>();

const { t } = useI18n({ useScope: 'global' });

const form = useTemplateRef<InstanceType<typeof RepullingTransactionForm>>('form');
const stateUpdated = ref<boolean>(false);

const { useIsActive } = useTaskCenter();

const taskRunning = useIsActive(ActivityKind.REPULLING);

const {
  modelAccountType: accountType,
  modelErrorMessages: errorMessages,
  modelEthStakingData: ethStakingData,
  modelFormData: formData,
  submit,
  submitting,
} = useRepullingTransactionSubmission({
  form,
  onExchangeEvents: repullExchangeEvents,
  onTransactions: repullTransactions,
  open: modelValue,
});
</script>

<template>
  <BigDialog
    :display="modelValue"
    :title="t('transactions.repulling.action')"
    :action="{
      disabled: loading || taskRunning,
      primary: t('transactions.repulling.action'),
      tooltip: loading ? t('transactions.repulling.loading_tooltip') : '',
    }"
    :loading="submitting || taskRunning"
    :prompt-on-close="stateUpdated"
    @confirm="submit()"
    @cancel="modelValue = false"
  >
    <RepullingTransactionForm
      ref="form"
      v-model="formData"
      v-model:account-type="accountType"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      v-model:eth-staking-data="ethStakingData"
    />
  </BigDialog>
</template>
