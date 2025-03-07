<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { AddTransactionHashPayload } from '@/types/history/events';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainStore } from '@/store/blockchain';
import { isBlockchain } from '@/types/blockchain/chains';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

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
