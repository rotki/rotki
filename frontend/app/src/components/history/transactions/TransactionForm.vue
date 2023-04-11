<script lang="ts" setup>
import { type GeneralAccount } from '@rotki/common/lib/account';
import { helpers, required } from '@vuelidate/validators';
import useVuelidate from '@vuelidate/core';
import { type Ref } from 'vue';
import { isValidTxHash } from '@/utils/text';
import {
  type AddTransactionHashPayload,
  type EvmChainAndTxHash
} from '@/types/history/tx';
import { type Writeable } from '@/types';
import { assert } from '@/utils/assertions';

withDefaults(
  defineProps<{
    value?: boolean;
  }>(),
  {
    value: false
  }
);

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();
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

const v$ = useVuelidate(
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

watch(v$, ({ $invalid }) => {
  emit('input', !$invalid);
});

const { txEvmChains, getEvmChainName } = useSupportedChains();
const txChains = useArrayMap(txEvmChains, x => x.id);

const { setMessage } = useMessageStore();
const { addTransactionHash } = useHistoryEvents();

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

  set(loading, true);
  const result = await addTransactionHash(payload);
  set(loading, false);

  if (result.success) {
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

const loading: Ref<boolean> = ref(false);

defineExpose({
  loading,
  save,
  reset
});
</script>
<template>
  <v-form :value="value">
    <v-row class="pt-4">
      <v-col cols="12">
        <blockchain-account-selector
          v-model="accounts"
          :chains="txChains"
          outlined
          no-padding
          flat
          :label="t('transactions.form.account.label')"
          :error-messages="v$.associatedAddress.$errors.map(e => e.$message)"
        />
      </v-col>

      <v-col cols="12">
        <v-text-field
          v-model="txHash"
          :label="t('common.tx_hash')"
          outlined
          :error-messages="v$.txHash.$errors.map(e => e.$message)"
        />
      </v-col>
    </v-row>
  </v-form>
</template>
