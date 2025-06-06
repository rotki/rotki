<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { RepullingTransactionPayload } from '@/types/history/events';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';

const modelValue = defineModel<RepullingTransactionPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const evmChain = useRefPropVModel(modelValue, 'evmChain');
const address = useRefPropVModel(modelValue, 'address');
const fromTimestamp = useRefPropVModel(modelValue, 'fromTimestamp');
const toTimestamp = useRefPropVModel(modelValue, 'toTimestamp');

const fromTimestampModel = computed({
  get: () => {
    const timestamp = get(fromTimestamp);
    if (!timestamp) {
      return '';
    }
    return convertFromTimestamp(timestamp);
  },
  set: (value: string) => {
    set(fromTimestamp, convertToTimestamp(value));
  },
});

const toTimestampModel = computed({
  get: () => {
    const timestamp = get(toTimestamp);
    if (!timestamp) {
      return '';
    }
    return convertFromTimestamp(timestamp);
  },
  set: (value: string) => {
    set(toTimestamp, convertToTimestamp(value));
  },
});

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { getChain, txEvmChains } = useSupportedChains();
const txChains = useArrayMap(txEvmChains, x => x.id);

const chainOptions = computed(() => {
  const accountChains = Object.entries(get(accountsPerChain))
    .filter(([_, accounts]) => accounts.length > 0)
    .map(([chain]) => chain);

  return [
    'evm',
    ...get(txChains).filter(chain => accountChains.includes(chain)),
  ];
});

const usableChains = computed<string[]>(() => {
  const evmChainVal = get(evmChain);
  if (!evmChainVal || evmChainVal === 'evm') {
    return get(chainOptions);
  }

  return [getChain(evmChainVal)];
});

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const model = get(modelValue);
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === model.address
          && (!model.evmChain || model.evmChain === 'evm' || model.evmChain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    const address = account
      ? getAccountAddress(account)
      : '';

    set(modelValue, {
      ...get(modelValue),
      address,
    });
  },
});

const rules = {
  address: { externalServerValidation: () => true },
  evmChain: { required },
  fromTimestamp: { required },
  toTimestamp: { required },
};

const states = {
  address,
  evmChain,
  fromTimestamp,
  toTimestamp,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

useFormStateWatcher(states, stateUpdated);

onBeforeUnmount(() => {
  set(errors, {});
});

watchImmediate(evmChain, (chain) => {
  if (chain === '') {
    set(evmChain, 'evm');
  }
});

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form class="flex flex-col gap-4">
    <div class="flex gap-2">
      <ChainSelect
        v-model="evmChain"
        class="max-w-[20rem]"
        :items="chainOptions"
        :error-messages="toMessages(v$.evmChain)"
      />
      <BlockchainAccountSelector
        v-model="accounts"
        class="flex-1"
        :chains="usableChains"
        hide-chain-icon
        outlined
        show-details
        multichain
        unique
        :custom-hint="t('transactions.repulling.address_hint')"
        :label="t('common.address')"
        :error-messages="toMessages(v$.address)"
        :no-data-text="t('transactions.form.account.no_address_found')"
      />
    </div>
    <div class="w-full flex gap-2">
      <div class="flex-1">
        <DateTimePicker
          v-model="fromTimestampModel"
          :label="t('generate.labels.start_date')"
          limit-now
          allow-empty
          :error-messages="toMessages(v$.fromTimestamp)"
        />
      </div>
      <div class="flex-1">
        <DateTimePicker
          v-model="toTimestampModel"
          :label="t('generate.labels.end_date')"
          limit-now
          :error-messages="toMessages(v$.toTimestamp)"
        />
      </div>
    </div>
  </form>
</template>
