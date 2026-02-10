<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { RepullingEthStakingPayload, RepullingTransactionPayload } from '@/types/history/events';
import { useTemplateRef } from 'vue';
import RepullingBlockchainForm from '@/components/history/events/tx/RepullingBlockchainForm.vue';
import RepullingEthStakingForm from '@/components/history/events/tx/RepullingEthStakingForm.vue';
import RepullingExchangeForm from '@/components/history/events/tx/RepullingExchangeForm.vue';

export type AccountType = 'blockchain' | 'exchange' | 'eth_staking';

const modelValue = defineModel<RepullingTransactionPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const accountType = defineModel<AccountType>('accountType', { default: 'blockchain', required: false });

const ethStakingData = defineModel<RepullingEthStakingPayload>('ethStakingData', { required: true });

const { t } = useI18n({ useScope: 'global' });

const blockchainForm = useTemplateRef<InstanceType<typeof RepullingBlockchainForm>>('blockchainForm');
const exchangeForm = useTemplateRef<InstanceType<typeof RepullingExchangeForm>>('exchangeForm');
const ethStakingForm = useTemplateRef<InstanceType<typeof RepullingEthStakingForm>>('ethStakingForm');

const accountTypeOptions = computed<{ text: string; value: AccountType }[]>(() => [
  { text: t('common.blockchain'), value: 'blockchain' },
  { text: t('common.exchange'), value: 'exchange' },
  { text: t('transactions.repulling.eth_staking.tab'), value: 'eth_staking' },
]);

watchImmediate(accountType, (type) => {
  if (!type) {
    set(accountType, 'blockchain');
  }
});

async function validate(): Promise<boolean> {
  const type = get(accountType);
  if (type === 'blockchain')
    return (await get(blockchainForm)?.validate()) ?? false;
  else if (type === 'exchange')
    return (await get(exchangeForm)?.validate()) ?? false;
  else
    return (await get(ethStakingForm)?.validate()) ?? false;
}

defineExpose({
  getExchangeData: () => get(exchangeForm)?.getExchangeData(),
  validate,
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiTabs
      v-model="accountType"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-5"
      color="primary"
    >
      <RuiTab
        v-for="option in accountTypeOptions"
        :key="option.value"
        :value="option.value"
      >
        {{ option.text }}
      </RuiTab>
    </RuiTabs>

    <RepullingBlockchainForm
      v-if="accountType === 'blockchain'"
      ref="blockchainForm"
      v-model="modelValue"
      v-model:error-messages="errors"
      v-model:state-updated="stateUpdated"
    />

    <RepullingExchangeForm
      v-else-if="accountType === 'exchange'"
      ref="exchangeForm"
      v-model="modelValue"
      v-model:error-messages="errors"
      v-model:state-updated="stateUpdated"
    />

    <RepullingEthStakingForm
      v-else
      ref="ethStakingForm"
      v-model="ethStakingData"
      v-model:error-messages="errors"
      v-model:state-updated="stateUpdated"
    />
  </div>
</template>
