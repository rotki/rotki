<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { InputMode } from '@/types/input-mode';
import AddressAccountForm from '@/components/accounts/management/types/AddressAccountForm.vue';
import ValidatorAccountForm from '@/components/accounts/management/types/ValidatorAccountForm.vue';
import XpubAccountForm from '@/components/accounts/management/types/XpubAccountForm.vue';
import {
  type AccountManageState,
  type StakingValidatorManage,
  type XpubManage,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import { isBtcChain } from '@/types/blockchain/chains';
import { XpubKeyType } from '@/types/blockchain/accounts';
import type { ValidationErrors } from '@/types/api/errors';

defineProps<{
  loading: boolean;
}>();

const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

const form = ref<
  | InstanceType<typeof AddressAccountForm>
  | InstanceType<typeof ValidatorAccountForm>
  | InstanceType<typeof XpubAccountForm>
>();

const modelValue = defineModel<AccountManageState>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const chain = useRefPropVModel(modelValue, 'chain');

const { isEvm } = useSupportedChains();

async function validate(): Promise<boolean> {
  const selectedForm = get(form);
  assert(selectedForm);
  if ('validate' in selectedForm)
    return await selectedForm.validate();

  logger.debug('selected form does not implement validate default to true');
  return true;
}

watch(modelValue, (modelValue) => {
  if ('xpub' in modelValue.data && modelValue.mode === 'edit')
    set(inputMode, InputMode.XPUB_ADD);
}, {
  immediate: true,
});

watch(chain, (chain) => {
  if (get(modelValue).mode === 'edit' || !chain)
    return;

  if (chain === Blockchain.ETH2) {
    set(modelValue, {
      mode: 'add',
      type: 'validator',
      chain: Blockchain.ETH2,
      data: {},
    } satisfies StakingValidatorManage);
  }
  else {
    const account = createNewBlockchainAccount();
    if (!get(isEvm(chain)))
      delete account.evm;

    set(modelValue, {
      ...account,
      chain,
    });
  }
});

watch(inputMode, (mode) => {
  const selectedChain = get(chain);
  if (get(modelValue).mode === 'edit' || !selectedChain)
    return;

  if (mode === InputMode.XPUB_ADD) {
    assert(isBtcChain(selectedChain));
    set(modelValue, {
      mode: 'add',
      type: 'xpub',
      chain: selectedChain,
      data: {
        tags: null,
        xpub: {
          xpub: '',
          derivationPath: '',
          xpubType: XpubKeyType.XPUB,
        },
      },
    } satisfies XpubManage);
  }
  else {
    const account = createNewBlockchainAccount();
    if (!get(isEvm(selectedChain)))
      delete account.evm;

    set(modelValue, {
      ...account,
      chain: selectedChain,
    });
  }
});

defineExpose({
  validate,
});
</script>

<template>
  <div data-cy="blockchain-balance-form">
    <AccountSelector
      v-if="chain"
      v-model:input-mode="inputMode"
      v-model:chain="chain"
      :edit-mode="modelValue.mode === 'edit'"
    />

    <ValidatorAccountForm
      v-if="modelValue.type === 'validator'"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errors"
      :loading="loading"
    />

    <XpubAccountForm
      v-else-if="modelValue.type === 'xpub'"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errors"
      :loading="loading"
    />

    <AgnosticAddressAccountForm
      v-else-if="modelValue.type === 'group'"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errors"
      :loading="loading"
    />

    <AddressAccountForm
      v-else
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errors"
      :loading="loading"
    >
      <template #selector="{ disabled, attrs }">
        <AllEvmChainsSelector
          v-bind="attrs"
          :disabled="disabled"
        />
      </template>
    </AddressAccountForm>
  </div>
</template>
