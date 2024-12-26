<script lang="ts" setup>
import { helpers, required } from '@vuelidate/validators';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useSupportedChains } from '@/composables/info/chains';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import { useRefPropVModel } from '@/utils/model';
import { useBlockchainStore } from '@/store/blockchain';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { isBlockchain } from '@/types/blockchain/chains';
import { useFormStateWatcher } from '@/composables/form';
import type { ValidationErrors } from '@/types/api/errors';
import type { AddTransactionHashPayload } from '@/types/history/events';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';

const modelValue = defineModel<AddTransactionHashPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n();

const txHash = useRefPropVModel(modelValue, 'txHash');

const { accounts: accountsPerChain } = storeToRefs(useBlockchainStore());

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const model = get(modelValue);
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === model.associatedAddress
          && (!model.evmChain || model.evmChain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    const associatedAddress = account
      ? getAccountAddress(account)
      : '';
    const evmChain = account && isBlockchain(account.chain) ? account.chain : '';

    set(modelValue, {
      ...get(modelValue),
      associatedAddress,
      evmChain,
    });
  },
});

const { txEvmChains } = useSupportedChains();
const txChains = useArrayMap(txEvmChains, x => x.id);

const rules = {
  associatedAddress: {
    required: helpers.withMessage(
      t('transactions.form.account.validation.non_empty'),
      (accounts: BlockchainAccount<AddressData>[]) => accounts.length > 0,
    ),
  },
  txHash: {
    isValidTxHash: helpers.withMessage(t('transactions.form.tx_hash.validation.valid'), isValidTxHash),
    required: helpers.withMessage(t('transactions.form.tx_hash.validation.non_empty'), required),
  },
};

const states = {
  associatedAddress: accounts,
  txHash,
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

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form class="flex flex-col gap-8">
    <BlockchainAccountSelector
      v-model="accounts"
      :chains="txChains"
      outlined
      :label="t('transactions.form.account.label')"
      :error-messages="toMessages(v$.associatedAddress)"
    />
    <RuiTextField
      v-model="txHash"
      :label="t('common.tx_hash')"
      variant="outlined"
      color="primary"
      :error-messages="toMessages(v$.txHash)"
    />
  </form>
</template>
