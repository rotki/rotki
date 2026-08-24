<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { WALLET_MODES } from '@/modules/wallet/constants';
import { useUnifiedProviders } from '@/modules/wallet/providers/use-unified-providers';
import ProviderSelectionDialog from '@/modules/wallet/ProviderSelectionDialog.vue';
import { isAmountExceeded, isTradeValid } from '@/modules/wallet/send/trade-send-utils';
import TradeAmountInput from '@/modules/wallet/send/TradeAmountInput.vue';
import TradeAssetSelector from '@/modules/wallet/send/TradeAssetSelector.vue';
import TradeConnectedAddressBadge from '@/modules/wallet/send/TradeConnectedAddressBadge.vue';
import TradeHistoryView from '@/modules/wallet/send/TradeHistoryView.vue';
import TradeRecipientAddress from '@/modules/wallet/send/TradeRecipientAddress.vue';
import { useBalanceQueries } from '@/modules/wallet/send/use-balance-queries';
import { useTradeAssetBalance } from '@/modules/wallet/send/use-trade-asset-balance';
import { useTradeGasEstimation } from '@/modules/wallet/send/use-trade-gas-estimation';
import { useTradeNetworkMatch } from '@/modules/wallet/send/use-trade-network-match';
import { useTradeRecipientWarning } from '@/modules/wallet/send/use-trade-recipient-warning';
import { useTradeWalletActions } from '@/modules/wallet/send/use-trade-wallet-actions';
import { TradableAssetKey, useTradableAsset } from '@/modules/wallet/use-tradable-asset';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import WalletConnectionButton from '@/modules/wallet/WalletConnectionButton.vue';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const amount = ref<string>('');
const asset = ref<string>('');
const assetChain = ref<string>(Blockchain.ETH);
const toAddress = ref<string>('');

const tradeAmountInputRef = useTemplateRef<InstanceType<typeof TradeAmountInput>>('tradeAmountInputRef');

const { getNativeAsset } = useSupportedChains();

const walletStore = useWalletStore();
const {
  connected,
  connectedAddress,
  isDisconnecting,
  isWalletConnect,
  preparing,
  supportedChainsForConnectedAccount,
  waitingForWalletConfirmation,
  walletMode,
} = storeToRefs(walletStore);
const { useQueryingBalances, warnUntrackedAddress } = useBalanceQueries(connected, connectedAddress);

const { switchToSelectedChain, wrongNetwork } = useTradeNetworkMatch(assetChain);

const tradableAsset = useTradableAsset(connectedAddress);
provide(TradableAssetKey, tradableAsset);
const { getAssetDetail } = tradableAsset;

const { availableProviders, isDetecting: detectingProviders, showProviderSelection } = useUnifiedProviders();

const isConnecting = logicOr(preparing, detectingProviders);

const assetDetail = getAssetDetail(asset, assetChain);
const isAssetResolved = computed<boolean>(() => !!get(assetDetail));

const isNativeAsset = computed<boolean>(() => {
  const chain = get(assetChain);
  const assetVal = get(asset);
  if (!chain || !assetVal)
    return false;

  return assetVal === getNativeAsset(chain);
});

const {
  clearError,
  connect,
  disconnect,
  errorMessage,
  selectProvider,
  send: sendTransaction,
  toggleConnection,
} = useTradeWalletActions();

const { showNeverInteractedWarning } = useTradeRecipientWarning({
  fromAddress: connectedAddress,
  toAddress,
});

const { estimatedGasFee, estimatingGas, gasEstimable } = useTradeGasEstimation({
  asset,
  chain: assetChain,
  isAssetResolved,
  isNativeAsset,
});

const { assetBalance, max, refreshAssetBalance, resetMax } = useTradeAssetBalance({
  address: connectedAddress,
  amount,
  asset,
  chain: assetChain,
  estimatedGasFee,
  gasEstimable,
});

const isWalletConnected = computed<boolean>(() => get(connected) && !!get(connectedAddress));

const amountExceeded = computed<boolean>(() => isAmountExceeded(get(amount), get(max)));

const valid = computed<boolean>(() => isTradeValid(get(amount), get(toAddress), get(max)));

function resetInput(): void {
  set(toAddress, '');
  set(amount, '');
  resetMax();
}

async function trackAddress(): Promise<void> {
  await router.push({
    path: '/accounts/evm/accounts',
    query: {
      add: 'true',
      addressToAdd: get(connectedAddress),
    },
  });
}

function setMax(): void {
  get(tradeAmountInputRef)?.setMax();
}

async function send(): Promise<void> {
  const sent = await sendTransaction({
    amount: get(amount),
    assetIdentifier: get(asset),
    chain: get(assetChain),
    native: get(isNativeAsset),
    to: get(toAddress),
  });

  if (sent)
    resetInput();
}

watch([assetChain, supportedChainsForConnectedAccount], ([currentChain, chainOptions]) => {
  if (!chainOptions.includes(currentChain))
    set(assetChain, chainOptions[0]);
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
        data-testid="untracked-warning"
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
        data-testid="querying-balances-warning"
      >
        {{ t('trade.warning.query_on_progress') }}
      </RuiAlert>
      <!-- Wallet Mode Selector -->

      <div class="flex items-end">
        <div class="grow">
          <template v-if="!isWalletConnected">
            <div class="text-rui-text-secondary text-caption uppercase mb-1">
              {{ t('trade.wallet_mode.label') }}
            </div>
            <RuiButtonGroup
              v-model="walletMode"
              variant="outlined"
              color="primary"
              required
              size="sm"
            >
              <RuiButton :model-value="WALLET_MODES.LOCAL_BRIDGE">
                {{ t('trade.wallet_mode.local_bridge') }}
              </RuiButton>
              <RuiButton :model-value="WALLET_MODES.WALLET_CONNECT">
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
        v-if="!isWalletConnected || isDisconnecting"
        size="lg"
        full-width
        data-testid="connect-action"
        :connected="isWalletConnected"
        :loading="isConnecting || isDisconnecting"
        @click="toggleConnection()"
      />
      <RuiButton
        v-else-if="warnUntrackedAddress"
        color="primary"
        size="lg"
        class="!w-full"
        data-testid="track-action"
        @click="trackAddress()"
      >
        {{ t('trade.actions.track') }}
      </RuiButton>
      <RuiButton
        v-else-if="wrongNetwork"
        color="primary"
        size="lg"
        class="!w-full"
        data-testid="switch-network-action"
        @click="switchToSelectedChain()"
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
        data-testid="send-action"
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
    data-testid="trade-error"
    @close="clearError()"
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
    @select-provider="selectProvider($event)"
  />
</template>
