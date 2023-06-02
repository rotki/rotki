<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Eth2Validator } from '@/types/balances';
import { type ValidationErrors } from '@/types/api/errors';
import { type BlockchainAccountWithBalance } from '@/types/blockchain/accounts';
import { type ActionStatus } from '@/types/action';

const { tc } = useI18n();

const validator = ref<Eth2Validator | null>(null);
const errorMessages = ref<ValidationErrors>({});

const { addEth2Validator, editEth2Validator } = useEthAccountsStore();
const { refreshAccounts, fetchAccounts } = useBlockchains();
const { updateEthStakingOwnership } = useEthBalancesStore();
const { setMessage } = useMessageStore();
const { valid, setSave, accountToEdit } = useAccountDialog();
const { pending, loading } = useAccountLoading();

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
  set(pending, true);
  const payload = get(validator);
  assert(payload);

  let result: ActionStatus<ValidationErrors | string>;
  const isEdit = isDefined(accountToEdit);
  if (isEdit) {
    result = await editEth2Validator(payload);
  } else {
    result = await addEth2Validator(payload);
  }

  if (result.success) {
    if (isDefined(accountToEdit)) {
      const newVar = get(accountToEdit);
      assert('ownershipPercentage' in newVar && newVar.ownershipPercentage);
      assert(payload.publicKey);
      assert(payload.ownershipPercentage);

      updateEthStakingOwnership(
        payload.publicKey,
        bigNumberify(newVar.ownershipPercentage),
        bigNumberify(payload.ownershipPercentage)
      );
      startPromise(fetchAccounts(Blockchain.ETH2));
    } else {
      startPromise(refreshAccounts(Blockchain.ETH2));
    }
  } else if (typeof result.message === 'string') {
    showMessage(
      result.message,
      payload.publicKey || payload.validatorIndex || '',
      isEdit
    );
  } else {
    set(errorMessages, result.message);
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
