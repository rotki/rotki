<script lang="ts" setup>
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
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
  txHash: {
    required: helpers.withMessage(t('transactions.form.tx_hash.validation.non_empty'), required),
    isValidTxHash: helpers.withMessage(t('transactions.form.tx_hash.validation.valid'), isValidTxHash),
  },
  associatedAddress: {
    required: helpers.withMessage(
      t('transactions.form.account.validation.non_empty'),
      (accounts: BlockchainAccount<AddressData>[]) => accounts.length > 0,
    ),
  },
};

const { setValidation, setSubmitFunc } = useHistoryTransactionsForm();

const v$ = setValidation(
  rules,
  {
    txHash,
    associatedAddress: accounts,
  },

  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

const { txEvmChains, getEvmChainName } = useSupportedChains();
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
    txHash: txHashVal,
    associatedAddress: getAccountAddress(accountsVal[0]),
    evmChain,
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
