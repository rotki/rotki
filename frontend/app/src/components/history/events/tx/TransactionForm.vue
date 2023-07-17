<script lang="ts" setup>
import { type GeneralAccount } from '@rotki/common/lib/account';
import { helpers, required } from '@vuelidate/validators';
import {
  type AddTransactionHashPayload,
  type EvmChainAndTxHash
} from '@/types/history/events';
import { type Writeable } from '@/types';
import { toMessages } from '@/utils/validation';

const { t } = useI18n();

const txHash = ref<string>('');
const accounts = ref<GeneralAccount[]>([]);

const errorMessages = ref<Record<string, string[]>>({});

const reset = () => {
  set(txHash, '');
  set(accounts, []);
};

const rules = {
  txHash: {
    required: helpers.withMessage(
      t('transactions.form.tx_hash.validation.non_empty').toString(),
      required
    ),
    isValidTxHash: helpers.withMessage(
      t('transactions.form.tx_hash.validation.valid').toString(),
      isValidTxHash
    )
  },
  associatedAddress: {
    required: helpers.withMessage(
      t('transactions.form.account.validation.non_empty').toString(),
      (accounts: GeneralAccount[]) => accounts.length > 0
    )
  }
};

const { valid, setValidation, setSubmitFunc } = useHistoryTransactionsForm();

const v$ = setValidation(
  rules,
  {
    txHash,
    associatedAddress: accounts
  },

  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

const { txEvmChains, getEvmChainName } = useSupportedChains();
const txChains = useArrayMap(txEvmChains, x => x.id);

const { setMessage } = useMessageStore();
const { addTransactionHash } = useHistoryTransactions();

const save = async (): Promise<EvmChainAndTxHash | null> => {
  const accountsVal = get(accounts);
  if (accountsVal.length === 0) {
    return null;
  }

  const evmChain = getEvmChainName(accountsVal[0].chain);
  assert(evmChain);

  const txHashVal = get(txHash);

  const payload: Writeable<AddTransactionHashPayload> = {
    txHash: txHashVal,
    associatedAddress: accountsVal[0].address,
    evmChain
  };

  const result = await addTransactionHash(payload);

  if (result.success) {
    reset();
    return {
      evmChain,
      txHash: txHashVal
    };
  }

  if (result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message
      });
    } else {
      set(errorMessages, result.message);
      await get(v$).$validate();
    }
  }

  return null;
};

setSubmitFunc(save);
</script>

<template>
  <VForm :value="valid">
    <VRow class="pt-4">
      <VCol cols="12">
        <BlockchainAccountSelector
          v-model="accounts"
          :chains="txChains"
          outlined
          no-padding
          flat
          :label="t('transactions.form.account.label')"
          :error-messages="toMessages(v$.associatedAddress)"
        />
      </VCol>

      <VCol cols="12">
        <VTextField
          v-model="txHash"
          :label="t('common.tx_hash')"
          outlined
          :error-messages="toMessages(v$.txHash)"
        />
      </VCol>
    </VRow>
  </VForm>
</template>
