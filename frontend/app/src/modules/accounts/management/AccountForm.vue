<script setup lang="ts">
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { camelCase } from 'es-toolkit';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import {
  type AccountManageState,
  createNewBlockchainAccount,
  type StakingValidatorManage,
  type XpubManage,
} from '@/modules/accounts/blockchain/use-account-manage';
import AccountFormApiKeyAlertContent from '@/modules/accounts/management/AccountFormApiKeyAlertContent.vue';
import AccountSelector from '@/modules/accounts/management/inputs/AccountSelector.vue';
import AddressAccountForm from '@/modules/accounts/management/types/AddressAccountForm.vue';
import AgnosticAddressAccountForm from '@/modules/accounts/management/types/AgnosticAddressAccountForm.vue';
import ValidatorAccountForm from '@/modules/accounts/management/types/ValidatorAccountForm.vue';
import XpubAccountForm from '@/modules/accounts/management/types/XpubAccountForm.vue';
import { isBtcChain } from '@/modules/core/common/chains';
import { InputMode } from '@/modules/core/common/input-mode';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const modelValue = defineModel<AccountManageState>({ required: true });

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  loading: boolean;
  chainIds: string[];
}>();

const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

const form = useTemplateRef<
  | InstanceType<typeof AddressAccountForm>
  | InstanceType<typeof ValidatorAccountForm>
  | InstanceType<typeof XpubAccountForm>
>('form');

const chain = useRefPropVModel(modelValue, 'chain');

const { isEvm, isSolanaChains, txEvmChains } = useSupportedChains();
const { t } = useI18n({ useScope: 'global' });
const { getApiKey } = useExternalApiKeys();

const { beaconRpcEndpoint, defaultEvmIndexerOrder, evmIndexersOrder } = storeToRefs(useGeneralSettingsStore());

/**
 * Checks if etherscan is the top priority indexer for a given chain.
 */
function isEtherscanTopPriority(chainId: string): boolean {
  const chainOrders = get(evmIndexersOrder);
  const evmChainName = camelCase(get(txEvmChains).find(c => c.id === chainId)?.evmChainName || '');
  const indexerOrder = evmChainName && chainOrders[evmChainName]
    ? chainOrders[evmChainName]
    : get(defaultEvmIndexerOrder);

  return indexerOrder[0] === EvmIndexer.ETHERSCAN;
}

/**
 * Checks if etherscan is the top priority for the selected chain(s).
 * For 'all', returns true if etherscan is top priority for any EVM chain.
 */
function shouldShowEtherscanWarning(selectedChain: string): boolean {
  if (selectedChain === 'all') {
    return get(txEvmChains).some(chain => isEtherscanTopPriority(chain.id));
  }

  if (!isEvm(selectedChain))
    return false;

  return isEtherscanTopPriority(selectedChain);
}

const missingApiKeyService = computed<'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc' | 'blockscout' | undefined>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  if (currentModelValue.mode !== 'add' || !selectedChain)
    return undefined;

  if (currentModelValue.type === 'validator' && !getApiKey('beaconchain')) {
    if (!get(beaconRpcEndpoint)) {
      return 'consensusRpc';
    }

    return 'beaconchain';
  }

  if (!getApiKey('etherscan') && shouldShowEtherscanWarning(selectedChain))
    return 'etherscan';

  if (!getApiKey('blockscout') && shouldShowEtherscanWarning(selectedChain))
    return 'blockscout';

  if (isSolanaChains(selectedChain) && !getApiKey('helius'))
    return 'helius';

  return undefined;
});

const showSolanaInitialAlert = computed<boolean>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  return currentModelValue.mode === 'add' && !!selectedChain && isSolanaChains(selectedChain);
});

const showBinanceEtherscanWarning = computed<boolean>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  return currentModelValue.mode === 'add' && selectedChain === 'all';
});

const warningExpanded = ref<boolean>(false);

type WarningType = 'solana' | 'apiKey' | 'binance';

interface WarningItem {
  type: WarningType;
  service?: 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc' | 'blockscout';
}

const warnings = computed<WarningItem[]>(() => {
  const result: WarningItem[] = [];
  if (get(missingApiKeyService))
    result.push({ service: get(missingApiKeyService), type: 'apiKey' });
  if (get(showSolanaInitialAlert))
    result.push({ type: 'solana' });
  if (get(showBinanceEtherscanWarning))
    result.push({ type: 'binance' });
  return result;
});

const hasMultipleWarnings = computed<boolean>(() => get(warnings).length > 1);

const visibleWarnings = computed<WarningItem[]>(() => {
  const all = get(warnings);
  if (all.length <= 1 || get(warningExpanded))
    return all;
  return all.slice(0, 1);
});

const hiddenWarningCount = computed<number>(() => get(warnings).length - get(visibleWarnings).length);

function toggleWarningExpanded(): void {
  set(warningExpanded, !get(warningExpanded));
}

async function validate(): Promise<boolean> {
  const selectedForm = get(form);
  assert(selectedForm);
  if ('validate' in selectedForm)
    return await selectedForm.validate();

  logger.debug('selected form does not implement validate default to true');
  return true;
}

async function handleDetectedXpub(key: string): Promise<void> {
  const selectedChain = get(chain);
  if (!selectedChain || !isBtcChain(selectedChain))
    return;

  set(inputMode, InputMode.XPUB_ADD);
  await nextTick();

  const current = get(modelValue);
  if (current.type !== 'xpub')
    return;

  set(modelValue, {
    ...current,
    data: {
      ...current.data,
      xpub: {
        ...current.data.xpub,
        xpub: key,
      },
    },
  });
}

async function handleDetectedAddress(address: string): Promise<void> {
  let targetChain = get(chain);
  if (!targetChain)
    return;

  if (targetChain === Blockchain.BTC && address.startsWith('bitcoincash:')) {
    targetChain = Blockchain.BCH;
    set(chain, targetChain);
    await nextTick();
  }

  set(inputMode, InputMode.MANUAL_ADD);
  await nextTick();
  set(modelValue, {
    chain: targetChain,
    data: [{ address, tags: null }],
    mode: 'add',
    type: 'account',
  });
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

  if (get(inputMode) === InputMode.XPUB_ADD)
    set(inputMode, InputMode.MANUAL_ADD);

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

defineExpose({
  validate,
});
</script>

<template>
  <div data-cy="blockchain-balance-form">
    <RuiAlert
      v-if="warnings.length > 0"
      type="warning"
      class="mb-6 -mt-2"
    >
      <ul :class="hasMultipleWarnings ? 'list-disc pl-4 space-y-1' : 'list-none pl-0'">
        <li
          v-for="warning in visibleWarnings"
          :key="warning.type"
        >
          <template v-if="warning.type === 'apiKey' && warning.service">
            <AccountFormApiKeyAlertContent :service="warning.service" />
          </template>
          <template v-else-if="warning.type === 'solana'">
            {{ t('blockchain_balances.solana_warning') }}
          </template>
          <template v-else-if="warning.type === 'binance'">
            {{ t('blockchain_balances.binance_warning') }}
          </template>
        </li>
      </ul>

      <RuiButton
        v-if="hasMultipleWarnings"
        variant="text"
        color="warning"
        size="sm"
        class="mt-1 -mb-1 ml-2.5"
        @click="toggleWarningExpanded()"
      >
        {{ warningExpanded ? t('common.actions.show_less') : t('common.actions.show_more_num', { count: hiddenWarningCount }) }}
        <template #append>
          <RuiIcon
            :name="warningExpanded ? 'lu-chevron-up' : 'lu-chevron-down'"
            size="16"
          />
        </template>
      </RuiButton>
    </RuiAlert>

    <AccountSelector
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
      @detected-address="startPromise(handleDetectedAddress($event))"
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
      @detected-xpub="startPromise(handleDetectedXpub($event))"
    />
  </div>
</template>
