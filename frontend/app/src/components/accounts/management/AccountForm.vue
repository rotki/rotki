<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { InputMode } from '@/types/input-mode';
import AddressAccountForm from '@/components/accounts/management/types/AddressAccountForm.vue';
import MetamaskAccountForm from '@/components/accounts/management/types/MetamaskAccountForm.vue';
import ValidatorAccountForm from '@/components/accounts/management/types/ValidatorAccountForm.vue';
import XpubAccountForm from '@/components/accounts/management/types/XpubAccountForm.vue';
import {
  type AccountManageAdd,
  type AccountManageState,
  type StakingValidatorManage,
  type XpubManage,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import { isBtcChain } from '@/types/blockchain/chains';
import { XpubKeyType } from '@/types/blockchain/accounts';
import type { ValidationErrors } from '@/types/api/errors';

const props = defineProps<{
  modelValue: AccountManageState;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: AccountManageState): void;
}>();

const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

const form = ref<
  | InstanceType<typeof AddressAccountForm>
  | InstanceType<typeof MetamaskAccountForm>
  | InstanceType<typeof ValidatorAccountForm>
  | InstanceType<typeof XpubAccountForm>
>();

const model = useSimpleVModel(props, emit);
const chain = useSimplePropVModel(props, 'chain', emit);
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

const { isEvm } = useSupportedChains();

async function validate(): Promise<boolean> {
  const selectedForm = get(form);
  assert(selectedForm);
  if ('validate' in selectedForm)
    return await selectedForm.validate();

  logger.debug('selected form does not implement validate default to true');
  return true;
}

async function importAccounts(): Promise<AccountManageAdd | null | false> {
  const selectedForm = get(form);
  assert(selectedForm);
  if (!('importAccounts' in selectedForm))
    return false;

  return await selectedForm.importAccounts();
}

watchImmediate(model, (model) => {
  if (model.type !== 'xpub')
    return;

  set(inputMode, InputMode.XPUB_ADD);
});

watch(chain, (chain) => {
  if (chain === Blockchain.ETH2) {
    set(model, {
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

    set(model, {
      ...account,
      chain,
    });
  }
});

watch(inputMode, (mode) => {
  if (mode === InputMode.XPUB_ADD) {
    const selectedChain = get(chain);
    assert(isBtcChain(selectedChain));
    set(model, {
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
    if (!get(isEvm(chain)))
      delete account.evm;

    set(model, {
      ...account,
      chain: get(chain),
    });
  }
});

defineExpose({
  validate,
  importAccounts,
});
</script>

<template>
  <div data-cy="blockchain-balance-form">
    <AccountSelector
      v-model:input-mode="inputMode"
      v-model:chain="chain"
      :edit-mode="model.mode === 'edit'"
    />

    <MetamaskAccountForm
      v-if="model.type === 'account' && inputMode === InputMode.METAMASK_IMPORT"
      ref="form"
      :chain="chain"
      :loading="loading"
    >
      <template #selector="{ disabled, attrs }">
        <AllEvmChainsSelector
          v-bind="attrs"
          :disabled="disabled"
        />
      </template>
    </MetamaskAccountForm>

    <ValidatorAccountForm
      v-else-if="model.type === 'validator'"
      ref="form"
      v-model="model"
      v-model:error-messages="errors"
      :loading="loading"
    />

    <XpubAccountForm
      v-else-if="model.type === 'xpub'"
      ref="form"
      v-model="model"
      v-model:error-messages="errors"
      :loading="loading"
    />

    <AddressAccountForm
      v-else
      ref="form"
      v-model="model"
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
