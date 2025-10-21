<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import { assert, Blockchain } from '@rotki/common';
import AccountFormApiKeyAlert from '@/components/accounts/management/AccountFormApiKeyAlert.vue';
import AccountSelector from '@/components/accounts/management/inputs/AccountSelector.vue';
import AddressAccountForm from '@/components/accounts/management/types/AddressAccountForm.vue';
import AgnosticAddressAccountForm from '@/components/accounts/management/types/AgnosticAddressAccountForm.vue';
import ValidatorAccountForm from '@/components/accounts/management/types/ValidatorAccountForm.vue';
import XpubAccountForm from '@/components/accounts/management/types/XpubAccountForm.vue';
import {
  type AccountManageState,
  createNewBlockchainAccount,
  type StakingValidatorManage,
  type XpubManage,
} from '@/composables/accounts/blockchain/use-account-manage';
import { useSupportedChains } from '@/composables/info/chains';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { XpubKeyType } from '@/types/blockchain/accounts';
import { isBtcChain } from '@/types/blockchain/chains';
import { InputMode } from '@/types/input-mode';
import { logger } from '@/utils/logging';
import { useRefPropVModel } from '@/utils/model';

const modelValue = defineModel<AccountManageState>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
  chainIds: string[];
}>();

const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

const form = ref<
  | InstanceType<typeof AddressAccountForm>
  | InstanceType<typeof ValidatorAccountForm>
  | InstanceType<typeof XpubAccountForm>
>();

const chain = useRefPropVModel(modelValue, 'chain');

const { isEvm, isSolanaChains } = useSupportedChains();
const { t } = useI18n({ useScope: 'global' });
const { apiKey, load: loadApiKeys } = useExternalApiKeys(t);

const missingApiKeyService = computed<'etherscan' | 'helius' | 'beaconchain' | undefined>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  if (currentModelValue.mode !== 'add' || !selectedChain)
    return undefined;

  if (currentModelValue.type === 'validator' && !get(apiKey('beaconchain')))
    return 'beaconchain';

  if ((selectedChain === 'evm' || get(isEvm(selectedChain))) && !get(apiKey('etherscan')))
    return 'etherscan';

  if (get(isSolanaChains(selectedChain)) && !get(apiKey('helius')))
    return 'helius';

  return undefined;
});

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

watchImmediate(chain, (chain) => {
  if (get(modelValue).mode === 'edit' || !chain)
    return;

  if (chain === Blockchain.ETH2) {
    set(modelValue, {
      chain: Blockchain.ETH2,
      data: {},
      mode: 'add',
      type: 'validator',
    } satisfies StakingValidatorManage);
  }
  else {
    const account = createNewBlockchainAccount();
    const newModelValue = {
      ...account,
      chain,
    };

    const data = get(modelValue).data;
    if (data && Array.isArray(data)) {
      newModelValue.data = data;
    }

    set(modelValue, newModelValue);
  }
});

watch(inputMode, (mode) => {
  const selectedChain = get(chain);
  if (get(modelValue).mode === 'edit' || !selectedChain)
    return;

  if (mode === InputMode.XPUB_ADD) {
    assert(isBtcChain(selectedChain));
    set(modelValue, {
      chain: selectedChain,
      data: {
        tags: null,
        xpub: {
          derivationPath: '',
          xpub: '',
          xpubType: XpubKeyType.XPUB,
        },
      },
      mode: 'add',
      type: 'xpub',
    } satisfies XpubManage);
  }
  else {
    const account = createNewBlockchainAccount();

    set(modelValue, {
      ...account,
      chain: selectedChain,
    });
  }
});

onBeforeMount(async () => {
  await loadApiKeys();
});

defineExpose({
  validate,
});
</script>

<template>
  <div data-cy="blockchain-balance-form">
    <AccountFormApiKeyAlert
      v-if="missingApiKeyService"
      :service="missingApiKeyService"
    />

    <AccountSelector
      v-if="chain"
      v-model:input-mode="inputMode"
      v-model:chain="chain"
      :chain-ids="chainIds"
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
    />
  </div>
</template>
