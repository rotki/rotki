<script lang="ts" setup>
import type { Exchange } from '@/types/exchanges';
import type { RepullingExchangeEventsPayload, RepullingTransactionPayload } from '@/types/history/events';
import { assert } from '@rotki/common';
import dayjs from 'dayjs';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RepullingTransactionForm from '@/components/history/events/tx/RepullingTransactionForm.vue';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useSupportedChains } from '@/composables/info/chains';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

const modelValue = defineModel<boolean>({ required: true });

withDefaults(defineProps<{
  loading?: boolean;
}>(), {
  loading: false,
});

const emit = defineEmits<{
  'refresh': [chains: string[]];
  'refresh-exchange-events': [exchanges: Exchange[]];
}>();

const formData = ref<RepullingTransactionPayload>(defaults());
const accountType = ref<'blockchain' | 'exchange'>('blockchain');

const { t } = useI18n({ useScope: 'global' });

const submitting = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof RepullingTransactionForm>>('form');
const stateUpdated = ref<boolean>(false);

const { setMessage } = useMessageStore();
const { repullingExchangeEvents, repullingTransactions } = useHistoryTransactions();
const { allTxChainsInfo, matchChain } = useSupportedChains();
const { useIsTaskRunning } = useTaskStore();

const taskRunning = useIsTaskRunning(TaskType.REPULLING_TXS);

function defaults(): RepullingTransactionPayload {
  return {
    address: '',
    chain: '',
    fromTimestamp: dayjs().subtract(1, 'year').unix(),
    toTimestamp: dayjs().unix(),
  };
}

async function submit(): Promise<void> {
  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return;

  const data = get(formData);
  const type = get(accountType);

  try {
    set(submitting, true);
    set(modelValue, false);

    if (type === 'exchange') {
      const exchange = formRef?.getExchangeData();
      const exchangePayload: RepullingExchangeEventsPayload = {
        fromTimestamp: data.fromTimestamp,
        location: exchange?.location || '',
        name: exchange?.name || '',
        toTimestamp: data.toTimestamp,
      };

      const newEventsDetected = await repullingExchangeEvents(exchangePayload);
      if (newEventsDetected && exchange) {
        emit('refresh-exchange-events', [exchange]);
        logger.debug('New exchange events detected');
      }
    }
    else {
      const chain = data.chain;
      const usedChain = chain && chain !== 'evm' ? chain : undefined;
      const blockchainPayload = {
        address: data.address || undefined,
        chain: usedChain,
        fromTimestamp: data.fromTimestamp,
        toTimestamp: data.toTimestamp,
      };

      const newTransactionsDetected = await repullingTransactions(blockchainPayload);
      if (newTransactionsDetected) {
        let chains: string[];
        if (chain === 'evm' || !chain) {
          chains = get(allTxChainsInfo).map(chain => chain.id);
        }
        else {
          const chainId = matchChain(chain);
          assert(chainId);
          chains = [chainId];
        }

        emit('refresh', chains);
        logger.debug(`New transactions detected ${chains.join(', ')}`);
      }
    }

    set(formData, defaults());
    set(accountType, 'blockchain');
  }
  catch (error: any) {
    let message = error.message;
    if (error instanceof ApiValidationError)
      message = error.getValidationErrors(data);

    if (typeof message === 'string') {
      setMessage({
        description: message,
      });
    }
    else {
      set(errorMessages, message);
      await formRef?.validate();
    }
  }
  finally {
    set(submitting, false);
  }
}
</script>

<template>
  <BigDialog
    :display="modelValue"
    :title="t('transactions.repulling.title')"
    :primary-action="t('transactions.repulling.action')"
    :action-disabled="loading || taskRunning"
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
    />
  </BigDialog>
</template>
