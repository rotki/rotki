<script lang="ts" setup>
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useMessageStore } from '@/store/message';
import { useSupportedChains } from '@/composables/info/chains';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useHistoryTransactionsForm } from '@/composables/history/events/tx/form';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { AddTransactionHashPayload, EvmChainAndTxHash } from '@/types/history/events';

const { t } = useI18n();

const txHash = ref<string>('');
const accounts = ref<BlockchainAccount<AddressData>[]>([]);

const errorMessages = ref<Record<string, string[]>>({});

function reset() {
  set(txHash, '');
  set(accounts, []);
}

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

const { setSubmitFunc, setValidation } = useHistoryTransactionsForm();

const v$ = setValidation(
  rules,
  {
    associatedAddress: accounts,
    txHash,
  },

  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

const { getEvmChainName, txEvmChains } = useSupportedChains();
const txChains = useArrayMap(txEvmChains, x => x.id);

const { setMessage } = useMessageStore();
const { addTransactionHash } = useHistoryTransactions();

async function save(): Promise<EvmChainAndTxHash | null> {
  const accountsVal = get(accounts);
  if (accountsVal.length === 0)
    return null;

  const evmChain = getEvmChainName(accountsVal[0].chain);
  assert(evmChain);

  const txHashVal = get(txHash);

  const payload: AddTransactionHashPayload = {
    associatedAddress: getAccountAddress(accountsVal[0]),
    evmChain,
    txHash: txHashVal,
  };

  const result = await addTransactionHash(payload);

  if (result.success) {
    reset();
    return {
      evmChain,
      txHash: txHashVal,
    };
  }

  if (result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message,
      });
    }
    else {
      set(errorMessages, result.message);
      await get(v$).$validate();
    }
  }

  return null;
}

setSubmitFunc(save);
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
