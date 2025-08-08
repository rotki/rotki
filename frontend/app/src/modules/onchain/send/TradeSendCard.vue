<script setup lang="ts">
import type { GasFeeEstimation, GetAssetBalancePayload } from '@/modules/onchain/types';
import type { EnhancedProviderDetail } from '@/modules/onchain/wallet-providers/provider-detection';
import { type BigNumber, bigNumberify, Blockchain, isValidEthAddress } from '@rotki/common';
import ProviderSelectionDialog from '@/components/wallets/ProviderSelectionDialog.vue';
import WalletConnectionButton from '@/components/wallets/WalletConnectionButton.vue';
import { useSupportedChains } from '@/composables/info/chains';
import TradeAmountInput from '@/modules/onchain/send/TradeAmountInput.vue';
import TradeAssetSelector from '@/modules/onchain/send/TradeAssetSelector.vue';
import TradeConnectedAddressBadge from '@/modules/onchain/send/TradeConnectedAddressBadge.vue';
import TradeHistoryView from '@/modules/onchain/send/TradeHistoryView.vue';
import TradeRecipientAddress from '@/modules/onchain/send/TradeRecipientAddress.vue';
import { useBalanceQueries } from '@/modules/onchain/send/use-balance-queries';
import { useTradableAsset } from '@/modules/onchain/use-tradable-asset';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useInjectedWallet } from '@/modules/onchain/wallet-bridge/use-injected-wallet';
import { useUnifiedProviders } from '@/modules/onchain/wallet-providers/use-unified-providers';
import { logger } from '@/utils/logging';
import { useTradeApi } from './use-trade-api';

const REJECTED_KEYWORDS = [
  'ACTION_REJECTED',
  'User cancelled',
  'User canceled',
  'User rejected',
];

const { t } = useI18n({ useScope: 'global' });

const amount = ref<string>('');
const asset = ref<string>('');
const assetChain = ref<string>(Blockchain.ETH);
const toAddress = ref<string>('');

const max = ref<string>('0');
const estimatedGasFee = ref<string>('0');
const assetBalance = ref<BigNumber>();

const estimatingGas = ref<boolean>(false);
const showNeverInteractedWarning = ref<boolean>(false);
const errorMessage = ref<string>('');
const currentGasEstimationController = ref<AbortController>();

const tradeAmountInputRef = useTemplateRef<InstanceType<typeof TradeAmountInput>>('tradeAmountInputRef');

const { getChainFromChainId, getChainIdFromChain } = useWalletHelper();
const { getEvmChainName, getNativeAsset } = useSupportedChains();

const walletStore = useWalletStore();
const {
  connected,
  connectedAddress,
  connectedChainId,
  isDisconnecting,
  isWalletConnect,
  preparing,
  supportedChainsForConnectedAccount,
  waitingForWalletConfirmation,
  walletMode,
} = storeToRefs(walletStore);
const { connect: connectWallet, disconnect: disconnectWallet, getGasFeeForChain, sendTransaction, switchNetwork } = walletStore;
const { useQueryingBalances, warnUntrackedAddress } = useBalanceQueries(connected, connectedAddress);

const { getAssetDetail } = useTradableAsset(connectedAddress);
const { getAssetBalance, getIsInteractedBefore } = useTradeApi();
const router = useRouter();

// Provider selection for wallet connection
const injectedWallet = useInjectedWallet();
const unifiedProviders = useUnifiedProviders();
const { availableProviders, isDetecting: detectingProviders, showProviderSelection } = unifiedProviders;

const isConnecting = logicOr(preparing, detectingProviders);

async function handleProviderSelection(provider: EnhancedProviderDetail): Promise<void> {
  try {
    await unifiedProviders.selectProvider(provider.info.uuid);
    await injectedWallet.connectToSelectedProvider();
  }
  catch (error: any) {
    const errorString = error.toString();
    if (REJECTED_KEYWORDS.some(keyword => errorString.includes(keyword))) {
      set(errorMessage, 'Wallet connection was rejected by user');
    }
    else if (errorString.includes('Request timeout')) {
      set(errorMessage, 'Connection request timed out. Please try again.');
    }
    else {
      set(errorMessage, `Failed to connect wallet: ${errorString}`);
    }
    logger.error('Provider selection failed:', error);
  }
}

const isNativeAsset = computed(() => {
  const chain = get(assetChain);
  const assetVal = get(asset);
  if (!chain || !assetVal) {
    return false;
  }

  const native = getNativeAsset(chain);
  return assetVal === native;
});

const assetDetail = getAssetDetail(asset, assetChain);

const wrongNetwork = computed(() => {
  const chainId = get(connectedChainId);
  if (!get(connected) || !chainId) {
    return false;
  }
  const chainIdOfConnectedNetwork = getChainFromChainId(chainId);
  return get(assetChain) !== chainIdOfConnectedNetwork;
});

const amountExceeded = computed(() => {
  const amountToBigNumber = bigNumberify(get(amount));
  const maxToBigNumber = bigNumberify(get(max));

  return amountToBigNumber.gt(maxToBigNumber);
});

const valid = computed<boolean>(() => {
  const amountToBigNumber = bigNumberify(get(amount));
  const to = get(toAddress);

  const amountValid = !amountToBigNumber.isNaN() && amountToBigNumber.gt(0);
  const toAddressValid = !!to && isValidEthAddress(to);

  return amountValid && toAddressValid && !get(amountExceeded);
});

function resetMax() {
  set(max, '0');
}

function resetInput() {
  set(toAddress, '');
  set(amount, '');
  resetMax();
}

function switchToDesireNetwork() {
  const chainId = getChainIdFromChain(get(assetChain));
  switchNetwork(BigInt(chainId));
}

async function trackAddress() {
  await router.push(
    {
      path: '/accounts/evm/accounts',
      query: {
        add: 'true',
        addressToAdd: get(connectedAddress),
      },
    },
  );
}

function setMax() {
  get(tradeAmountInputRef)?.setMax();
}

function updateMaxAmountForAsset() {
  const balance = get(assetBalance);
  if (balance) {
    set(max, balance.minus(get(estimatedGasFee)).toFixed());
  }
  else {
    resetMax();
  }
}

async function estimateGas(currentAsset: string): Promise<GasFeeEstimation | undefined> {
  // Create a new controller for this request
  set(currentGasEstimationController, new AbortController());
  set(estimatingGas, true);

  const abortEstimationPromise = new Promise<GasFeeEstimation>((_, reject) => {
    get(currentGasEstimationController)?.signal.addEventListener('abort', () => {
      reject(new Error('Gas estimation cancelled'));
    });
  });
  const gasFeeEstimation = await Promise.race([
    getGasFeeForChain(),
    abortEstimationPromise,
  ]);

  if (currentAsset !== get(asset)) {
    return undefined;
  }
  return gasFeeEstimation;
}

async function send() {
  const isNative = get(isNativeAsset);
  const assetVal = get(asset);

  const params = {
    amount: get(amount),
    assetIdentifier: assetVal,
    chain: get(assetChain),
    native: isNative,
    to: get(toAddress),
  };

  try {
    set(errorMessage, '');
    await sendTransaction(params);
    resetInput();
  }
  catch (error: any) {
    const errorString = error.toString();
    if (REJECTED_KEYWORDS.some(keyword => errorString.includes(keyword))) {
      set(errorMessage, 'Request is rejected by user');
    }
    else {
      set(errorMessage, errorString);
    }
  }
}

async function refreshAssetBalance() {
  set(amount, '');
  set(assetBalance, undefined);

  const chain = get(assetChain);
  const assetVal = get(asset);
  const address = get(connectedAddress);

  if (!chain || !assetVal || !address) {
    return;
  }

  const evmChain = getEvmChainName(chain);

  if (!evmChain) {
    return;
  }

  const payload: GetAssetBalancePayload = {
    address,
    asset: assetVal,
    evmChain,
  };

  try {
    const response = await getAssetBalance(payload);
    if (get(asset) === payload.asset) {
      set(assetBalance, response);
    }
  }
  catch (error) {
    logger.error(error);
  }
}

async function onConnectClicked() {
  if (get(connected)) {
    await disconnect();
  }
  else {
    await connect();
  }
}

async function connect() {
  try {
    set(errorMessage, '');
    await connectWallet();
  }
  catch (error: any) {
    logger.error(error);
    set(errorMessage, error.message);
  }
}

async function disconnect() {
  try {
    set(errorMessage, '');
    await disconnectWallet();
  }
  catch (error: any) {
    logger.error(error);
    set(errorMessage, error.message);
  }
}

watch([assetChain, supportedChainsForConnectedAccount], ([currentChain, chainOptions]) => {
  if (!chainOptions.includes(currentChain)) {
    set(assetChain, chainOptions[0]);
  }
});

watch([connectedAddress, toAddress], async ([fromAddress, toAddress]) => {
  if (!fromAddress || !toAddress || !isValidEthAddress(toAddress)) {
    set(showNeverInteractedWarning, false);
    return;
  }

  try {
    const result = await getIsInteractedBefore(fromAddress, toAddress);
    set(showNeverInteractedWarning, !result);
  }
  catch (error: any) {
    set(showNeverInteractedWarning, false);
    logger.error(error);
  }
});

watch([assetChain, asset, connectedAddress], async () => {
  await refreshAssetBalance();
});

// calculate the gas fee estimation
watchImmediate([
  asset,
  assetChain,
  connectedChainId,
], async ([currentAsset, chain, connectedChainId]) => {
  if (!get(connected) || !chain || !currentAsset || !get(assetDetail)) {
    resetMax();
    return;
  }

  // Cancel previous request if it exists
  const controller = get(currentGasEstimationController);
  if (controller) {
    controller.abort();
  }

  if (!get(isNativeAsset)) {
    set(estimatedGasFee, '0');
    return;
  }

  try {
    if (getChainIdFromChain(chain) === connectedChainId) {
      const gasFeeEstimation = await estimateGas(currentAsset);
      if (gasFeeEstimation) {
        const { gasFee } = gasFeeEstimation;
        set(estimatedGasFee, gasFee);
        return;
      }
    }

    set(estimatedGasFee, '0');
  }
  catch (error: any) {
    if (error.message !== 'Gas estimation cancelled') {
      set(estimatedGasFee, '0');
      logger.error(error);
    }
  }
  finally {
    set(currentGasEstimationController, undefined);
    set(estimatingGas, false);
  }
});

watchImmediate(connectedChainId, (curr, prev) => {
  if (!isDefined(curr) || curr === prev) {
    return;
  }

  set(assetChain, getChainFromChainId(curr));
});

watch([estimatedGasFee, assetBalance], () => {
  updateMaxAmountForAsset();
});
</script>

<template>
  <RuiCard
    class="!rounded-xl"
    no-padding
  >
    <div class="p-6 flex flex-col gap-6 border-b border-default">
      <RuiAlert
        v-if="warnUntrackedAddress && !isDisconnecting"
        type="warning"
      >
        {{ t('trade.warning.not_tracked') }}
        <RuiButton
          color="primary"
          size="sm"
          class="mt-2"
          @click="trackAddress()"
        >
          {{ t('trade.actions.track') }}
        </RuiButton>
      </RuiAlert>
      <RuiAlert
        v-if="useQueryingBalances"
        type="warning"
      >
        {{ t('trade.warning.query_on_progress') }}
      </RuiAlert>
      <!-- Wallet Mode Selector -->

      <div class="flex items-end">
        <div class="grow">
          <template v-if="!connected">
            <div class="text-rui-text-secondary text-caption uppercase mb-1">
              {{ t('trade.wallet_mode.label') }}
            </div>
            <RuiButtonGroup
              v-model="walletMode"
              variant="outlined"
              color="primary"
              :required="true"
              size="sm"
            >
              <RuiButton model-value="local-bridge">
                {{ t('trade.wallet_mode.local_bridge') }}
              </RuiButton>
              <RuiButton model-value="walletconnect">
                {{ t('trade.wallet_mode.wallet_connect') }}
              </RuiButton>
            </RuiButtonGroup>
          </template>
        </div>
        <div class="flex gap-2">
          <TradeConnectedAddressBadge
            :loading="isConnecting"
            @connect="connect()"
            @disconnect="disconnect()"
          />
          <TradeHistoryView />
        </div>
      </div>
    </div>
    <div class="p-6">
      <TradeAmountInput
        ref="tradeAmountInputRef"
        v-model="amount"
        :loading="estimatingGas"
        :max="max"
        :amount-exceeded="amountExceeded"
        :chain="assetChain"
        :address="!warnUntrackedAddress ? connectedAddress : undefined"
        :asset="asset"
      />
      <TradeAssetSelector
        v-model="asset"
        v-model:chain="assetChain"
        :amount="assetBalance"
        :address="!warnUntrackedAddress ? connectedAddress : undefined"
        @set-max="setMax()"
        @refresh="refreshAssetBalance()"
      />
      <TradeRecipientAddress
        v-model="toAddress"
        :chain="assetChain"
        :show-warning="showNeverInteractedWarning"
      />
    </div>
    <div class="p-6 border-t border-default">
      <WalletConnectionButton
        v-if="!connected || isDisconnecting"
        size="lg"
        full-width
        :loading="isConnecting || isDisconnecting"
        @click="onConnectClicked()"
      />
      <RuiButton
        v-else-if="warnUntrackedAddress"
        color="primary"
        size="lg"
        class="!w-full"
        @click="trackAddress()"
      >
        {{ t('trade.actions.track') }}
      </RuiButton>
      <RuiButton
        v-else-if="wrongNetwork"
        color="primary"
        size="lg"
        class="!w-full"
        @click="switchToDesireNetwork()"
      >
        {{ t('trade.actions.change_network') }}
      </RuiButton>
      <RuiButton
        v-else
        color="primary"
        size="lg"
        class="!w-full"
        :disabled="!valid || estimatingGas || !assetBalance"
        :loading="preparing"
        @click="send()"
      >
        {{ t('trade.actions.send') }}
      </RuiButton>
    </div>
  </RuiCard>
  <RuiAlert
    v-if="errorMessage"
    type="error"
    class="whitespace-break-spaces mt-4 overflow-hidden [&>div:first-child]:overflow-hidden [&>div:first-child>div:last-child]:overflow-hidden"
    closeable
    @close="errorMessage = ''"
  >
    <div class="overflow-hidden">
      {{ errorMessage }}
    </div>
  </RuiAlert>
  <RuiAlert
    v-if="waitingForWalletConfirmation"
    type="info"
    class="mt-4"
  >
    {{
      isWalletConnect
        ? t('trade.waiting_for_confirmation.wallet_connect')
        : t('trade.waiting_for_confirmation.not_wallet_connect')
    }}
  </RuiAlert>

  <!-- Provider Selection Dialog -->
  <ProviderSelectionDialog
    v-model="showProviderSelection"
    :providers="availableProviders"
    :loading="detectingProviders"
    @select-provider="handleProviderSelection($event)"
  />
</template>
