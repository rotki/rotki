<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Eth2Validator } from '@/types/balances';
import { type ValidationErrors } from '@/types/api/errors';
import { type BlockchainAccountWithBalance } from '@/types/blockchain/accounts';

const validator = ref<Eth2Validator | null>(null);
const errorMessages = ref<ValidationErrors>({});

const { addEth2Validator, editEth2Validator } = useEthAccountsStore();
const { refreshAccounts } = useBlockchains();
const { setMessage } = useMessageStore();
const { valid, setSave, accountToEdit } = useAccountDialog();
const { pending, loading } = useAccountLoading();
const { t } = useI18n();

const showMessage = (message: string, id: string, edit: boolean) => {
  let description: string;
  let title: string;

  if (edit) {
    title = t('actions.edit_eth2_validator.error.title');
    description = t('actions.edit_eth2_validator.error.description', {
      id,
      message
    });
  } else {
    title = t('actions.add_eth2_validator.error.title');
    description = t('actions.add_eth2_validator.error.description', {
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
      :disabled="loading || !!accountToEdit"
      :error-messages="errorMessages"
      @update:validator="validator = $event"
    />
  </v-form>
</template>
