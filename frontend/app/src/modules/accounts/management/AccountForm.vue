<script setup lang="ts">
import type {
  AccountManageState,
  StakingValidatorManage,
  XpubManage,
} from '@/modules/accounts/blockchain/use-account-manage';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { camelCase } from 'es-toolkit';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { createNewAccountForChain } from '@/modules/accounts/blockchain/new-account-state';
import AccountFormApiKeyAlertContent from '@/modules/accounts/management/AccountFormApiKeyAlertContent.vue';
import AccountSelector from '@/modules/accounts/management/inputs/AccountSelector.vue';
import AddressAccountForm from '@/modules/accounts/management/types/AddressAccountForm.vue';
import AgnosticAddressAccountForm from '@/modules/accounts/management/types/AgnosticAddressAccountForm.vue';
import BtcAccountForm from '@/modules/accounts/management/types/BtcAccountForm.vue';
import ValidatorAccountForm from '@/modules/accounts/management/types/ValidatorAccountForm.vue';
import { isBtcChain } from '@/modules/core/common/chains';
import { InputMode } from '@/modules/core/common/input-mode';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { useSetting } from '@/modules/settings/use-setting';

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
  | InstanceType<typeof BtcAccountForm>
>('form');

// Read-only, because a chain is chosen rather than edited: `selectChain` below is the only thing
// that answers a choice, and it answers it with a whole state rather than a field.
const chain = computed<string | undefined>(() => get(modelValue).chain);

/**
 * A validator edit only ever reaches a state that holds a validator, which is what the guard says.
 * Narrowing first is what lets the rest of the state be carried over as itself, rather than a field
 * being written onto whichever variant happens to be there.
 */
function setValidator(data: StakingValidatorManage['data']): void {
  const state = get(modelValue);
  if (state.type !== 'validator')
    return;

  set(modelValue, { ...state, data });
}

const { getChainName, isEarlyIntegrationChain, isEvm, isSolanaChains, txEvmChains } = useSupportedChains();
const { t } = useI18n({ useScope: 'global' });
const { getApiKey } = useExternalApiKeys();

const beaconRpcEndpoint = useSetting('beaconRpcEndpoint');
const defaultEvmIndexerOrder = useSetting('defaultEvmIndexerOrder');
const evmIndexersOrder = useSetting('evmIndexersOrder');

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

/** Without a beaconchain key, validators fall back to a consensus RPC, which needs its own endpoint. */
function validatorKeyService(): 'beaconchain' | 'consensusRpc' | undefined {
  if (getApiKey('beaconchain'))
    return undefined;

  return get(beaconRpcEndpoint) ? 'beaconchain' : 'consensusRpc';
}

/** Both indexers are only worth warning about on chains that actually use them. */
function indexerKeyService(chain: string): 'etherscan' | 'blockscout' | undefined {
  if (!shouldShowEtherscanWarning(chain))
    return undefined;

  if (!getApiKey('etherscan'))
    return 'etherscan';

  return getApiKey('blockscout') ? undefined : 'blockscout';
}

const missingApiKeyService = computed<'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc' | 'blockscout' | undefined>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  if (currentModelValue.mode !== 'add' || !selectedChain)
    return undefined;

  if (currentModelValue.type === 'validator')
    return validatorKeyService();

  if (isSolanaChains(selectedChain))
    return getApiKey('helius') ? undefined : 'helius';

  return indexerKeyService(selectedChain);
});

const showSolanaInitialAlert = computed<boolean>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  return currentModelValue.mode === 'add' && !!selectedChain && isSolanaChains(selectedChain);
});

const earlyIntegrationChain = computed<string | undefined>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  if (currentModelValue.mode === 'add' && selectedChain && isEarlyIntegrationChain(selectedChain))
    return selectedChain;
  return undefined;
});

const showBinanceEtherscanWarning = computed<boolean>(() => {
  const selectedChain = get(chain);
  const currentModelValue = get(modelValue);

  return currentModelValue.mode === 'add' && selectedChain === 'all';
});

const warningExpanded = ref<boolean>(false);

type WarningType = 'solana' | 'apiKey' | 'binance' | 'earlyChain';

interface WarningItem {
  type: WarningType;
  service?: 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc' | 'blockscout';
  chain?: string;
}

function isBeaconchainService(service: WarningItem['service']): boolean {
  return service === 'beaconchain' || service === 'consensusRpc';
}

const beaconchainInfo = computed<WarningItem | undefined>(() => {
  const service = get(missingApiKeyService);
  if (!service || !isBeaconchainService(service))
    return undefined;
  return { service, type: 'apiKey' };
});

const warnings = computed<WarningItem[]>(() => {
  const result: WarningItem[] = [];
  const service = get(missingApiKeyService);
  if (service && !isBeaconchainService(service))
    result.push({ service, type: 'apiKey' });
  if (get(showSolanaInitialAlert))
    result.push({ type: 'solana' });
  const earlyChain = get(earlyIntegrationChain);
  if (earlyChain)
    result.push({ chain: earlyChain, type: 'earlyChain' });
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

  if (targetChain === Blockchain.BTC && address.startsWith('bitcoincash:'))
    targetChain = Blockchain.BCH;

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

/**
 * Answers a chosen chain with a whole state.
 *
 * Each chain implies a kind of account: eth2 a validator, anything else an address account, each
 * with a different shape of `data` and a different form below to edit it in. So this replaces the
 * state rather than writing a field into it — writing the chain alone would leave it paired with
 * the previous kind, which is a state the union does not admit and nothing downstream expects.
 *
 * An account being edited already exists on its chain, so there is nothing to choose.
 */
function selectChain(next: string | undefined): void {
  if (!next || get(modelValue).mode === 'edit')
    return;

  if (get(inputMode) === InputMode.XPUB_ADD)
    set(inputMode, InputMode.MANUAL_ADD);

  const state = createNewAccountForChain(next);
  if (state.type === 'validator') {
    set(modelValue, state);
    return;
  }

  // Only the chain was answered, so addresses already typed still answer a different question.
  const data = get(modelValue).data;
  set(modelValue, {
    ...state,
    ...(Array.isArray(data) ? { data } : {}),
  });
}

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
          xpubType: selectedChain === Blockchain.BCH ? XpubKeyType.XPUB : XpubKeyType.ZPUB,
        },
      },
      mode: 'add',
      type: 'xpub',
    } satisfies XpubManage);
  }
  else {
    set(modelValue, createNewAccountForChain(selectedChain));
  }
});

defineExpose({
  validate,
});
</script>

<template>
  <div data-testid="blockchain-balance-form">
    <RuiAlert
      v-if="beaconchainInfo?.service"
      type="info"
      class="mb-6 -mt-2"
    >
      <AccountFormApiKeyAlertContent :service="beaconchainInfo.service" />
    </RuiAlert>

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
          <template v-else-if="warning.type === 'earlyChain' && warning.chain">
            {{ t('blockchain_balances.early_chain_warning', { chain: getChainName(warning.chain) }) }}
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
      :chain="chain"
      :chain-ids="chainIds"
      :edit-mode="modelValue.mode === 'edit'"
      @update:chain="selectChain($event)"
    />

    <ValidatorAccountForm
      v-if="modelValue.type === 'validator'"
      ref="form"
      v-model:error-messages="errors"
      :validator="modelValue.data"
      :edit-mode="modelValue.mode === 'edit'"
      :loading="loading"
      @update:validator="setValidator($event)"
    />

    <BtcAccountForm
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
