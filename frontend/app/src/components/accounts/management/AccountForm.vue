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
  value: AccountManageState;
  loading: boolean;
  errorMessages: ValidationErrors;
}>();

const emit = defineEmits<{
  (e: 'input', value: AccountManageState): void;
}>();

const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

const form = ref<
  InstanceType<typeof AddressAccountForm> |
  InstanceType<typeof MetamaskAccountForm> |
  InstanceType<typeof ValidatorAccountForm> |
  InstanceType<typeof XpubAccountForm>
>();

const model = useSimpleVModel(props, emit);
const chain = useSimplePropVModel(props, 'chain', emit);

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
    set(model, {
      ...createNewBlockchainAccount(),
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
    set(model, {
      ...createNewBlockchainAccount(),
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
      :input-mode.sync="inputMode"
      :chain.sync="chain"
      :edit-mode="model.mode === 'edit'"
    />

    <MetamaskAccountForm
      v-if="model.type === 'account' && inputMode === InputMode.METAMASK_IMPORT"
      ref="form"
      :chain="chain"
      :loading="loading"
    >
      <template #selector="{ disabled, attrs, on }">
        <AllEvmChainsSelector
          v-bind="attrs"
          :disabled="disabled"
          v-on="on"
        />
      </template>
    </MetamaskAccountForm>

    <ValidatorAccountForm
      v-else-if="model.type === 'validator'"
      ref="form"
      v-model="model"
      :loading="loading"
      :error-messages="errorMessages"
    />

    <XpubAccountForm
      v-else-if="model.type === 'xpub'"
      ref="form"
      v-model="model"
      :loading="loading"
      :error-messages="errorMessages"
    />

    <AddressAccountForm
      v-else
      ref="form"
      v-model="model"
      :loading="loading"
      :error-messages="errorMessages"
    >
      <template #selector="{ disabled, attrs, on }">
        <AllEvmChainsSelector
          v-bind="attrs"
          :disabled="disabled"
          v-on="on"
        />
      </template>
    </AddressAccountForm>
  </div>
</template>
