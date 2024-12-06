<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { InputMode } from '@/types/input-mode';
import {
  type AccountManageState,
  type StakingValidatorManage,
  type XpubManage,
  createNewBlockchainAccount,
} from '@/composables/accounts/blockchain/use-account-manage';
import { isBtcChain } from '@/types/blockchain/chains';
import { XpubKeyType } from '@/types/blockchain/accounts';
import { useRefPropVModel } from '@/utils/model';
import { logger } from '@/utils/logging';
import AddressAccountForm from '@/components/accounts/management/types/AddressAccountForm.vue';
import ValidatorAccountForm from '@/components/accounts/management/types/ValidatorAccountForm.vue';
import XpubAccountForm from '@/components/accounts/management/types/XpubAccountForm.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import AllEvmChainsSelector from '@/components/accounts/management/inputs/AllEvmChainsSelector.vue';
import AgnosticAddressAccountForm from '@/components/accounts/management/types/AgnosticAddressAccountForm.vue';
import AccountSelector from '@/components/accounts/management/inputs/AccountSelector.vue';
import type { ValidationErrors } from '@/types/api/errors';

const modelValue = defineModel<AccountManageState>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
}>();

const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

const form = ref<
  | InstanceType<typeof AddressAccountForm>
  | InstanceType<typeof ValidatorAccountForm>
  | InstanceType<typeof XpubAccountForm>
>();

const chain = useRefPropVModel(modelValue, 'chain');

const { isEvm } = useSupportedChains();
const { t } = useI18n();
const { apiKey, load: loadApiKeys } = useExternalApiKeys(t);
const router = useRouter();

const etherscanApiKeyAlert = computed(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  if (
    selectedChain
    && get(isEvm(selectedChain))
    && currentModelValue.mode === 'add'
    && 'evm' in currentModelValue
    && !currentModelValue.evm
  ) {
    const chainName = selectedChain === 'eth' ? 'ethereum' : selectedChain;
    const displayChain = toHumanReadable(selectedChain, 'sentence');
    if (!get(apiKey('etherscan', chainName))) {
      return {
        action: t('notification_messages.missing_api_key.action'),
        chainName,
        message: t('external_services.etherscan.api_key_message', { chain: displayChain }),
      };
    }
  }

  return null;
});

function navigateToApiKeySettings(chainName: string) {
  router.push({ hash: `#${chainName}`, path: '/api-keys/external' });
}

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
      chain: Blockchain.ETH2,
      data: {},
      mode: 'add',
      type: 'validator',
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
    if (!get(isEvm(selectedChain)))
      delete account.evm;

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
    <RuiAlert
      v-if="etherscanApiKeyAlert"
      type="warning"
      class="mb-4"
    >
      {{ etherscanApiKeyAlert.message }}
      <a
        href="#"
        class="font-medium underline"
        @click.prevent="navigateToApiKeySettings(etherscanApiKeyAlert.chainName)"
      >
        {{ etherscanApiKeyAlert.action }}
      </a>
    </RuiAlert>

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
