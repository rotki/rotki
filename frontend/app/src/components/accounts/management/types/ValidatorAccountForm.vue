<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Eth2Validator } from '@/types/balances';
import { assert } from '@/utils/assertions';
import { startPromise } from '@/utils';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useBlockchainStore } from '@/store/blockchain';
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import { useMessageStore } from '@/store/message';
import { type ValidationErrors } from '@/types/api/errors';
import { type BlockchainAccountWithBalance } from '@/store/balances/types';

const validator = ref<Eth2Validator | null>(null);
const errorMessages = ref<ValidationErrors>({});

const { addEth2Validator, editEth2Validator } = useEthAccountsStore();
const { refreshAccounts } = useBlockchainStore();
const { setMessage } = useMessageStore();
const { valid, setSave, accountToEdit } = useAccountDialog();
const { pending, loading } = useAccountLoading();
const { tc } = useI18n();

const showMessage = (message: string, id: string, edit: boolean) => {
  let description: string;
  let title: string;

  if (edit) {
    title = tc('actions.edit_eth2_validator.error.title');
    description = tc('actions.edit_eth2_validator.error.description', 0, {
      id,
      message
    });
  } else {
    title = tc('actions.add_eth2_validator.error.title');
    description = tc('actions.add_eth2_validator.error.description', 0, {
      id,
      message
    });
  }

  setMessage({
    description,
    title,
    success: false
  });
};

const save = async () => {
  const edit = !!get(accountToEdit);

  set(pending, true);
  const payload = get(validator);
  assert(payload);
  const result = await (edit
    ? editEth2Validator(payload)
    : addEth2Validator(payload));
  if (result.success) {
    startPromise(refreshAccounts(Blockchain.ETH2));
  } else if (result.message) {
    if (typeof result.message === 'string') {
      showMessage(
        result.message,
        payload.publicKey || payload.validatorIndex || '',
        edit
      );
    } else {
      set(errorMessages, result.message);
    }
  }

  set(pending, false);
  return result.success;
};

const setValidator = (acc: BlockchainAccountWithBalance): void => {
  assert('ownershipPercentage' in acc);
  set(validator, {
    publicKey: acc.address,
    validatorIndex: acc.label,
    ownershipPercentage: acc.ownershipPercentage
  });
};

watch(accountToEdit, edit => {
  if (!edit) {
    set(validator, null);
  } else {
    setValidator(edit);
  }
});

onMounted(() => {
  setSave(save);

  const acc = get(accountToEdit);
  if (acc) {
    setValidator(acc);
  } else {
    set(validator, null);
  }
});
</script>

<template>
  <v-form v-model="valid">
    <eth2-input
      :validator="validator"
      :disabled="loading"
      :error-messages="errorMessages"
      @update:validator="validator = $event"
    />
  </v-form>
</template>
