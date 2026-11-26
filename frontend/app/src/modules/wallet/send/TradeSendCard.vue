<script setup lang="ts">
import { RuiAlert, RuiButton, RuiCard } from '@rotki/ui-library';
import { logicOr } from '@vueuse/math';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useUnifiedProviders } from '@/modules/wallet/providers/use-unified-providers';
import ProviderSelectionDialog from '@/modules/wallet/ProviderSelectionDialog.vue';
import TradeAmountInput from '@/modules/wallet/send/TradeAmountInput.vue';
import TradeAssetSelector from '@/modules/wallet/send/TradeAssetSelector.vue';
import TradeRecipientAddress from '@/modules/wallet/send/TradeRecipientAddress.vue';
import TradeSendHeader from '@/modules/wallet/send/TradeSendHeader.vue';
import { useBalanceQueries } from '@/modules/wallet/send/use-balance-queries';
import { useTradeSendForm } from '@/modules/wallet/send/use-trade-send-form';
import { useTradeWalletActions } from '@/modules/wallet/send/use-trade-wallet-actions';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import WalletConnectionButton from '@/modules/wallet/WalletConnectionButton.vue';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const tradeAmountInputRef = useTemplateRef<InstanceType<typeof TradeAmountInput>>('tradeAmountInputRef');

const walletStore = useWalletStore();
const {
  connected,
  connectedAddress,
  isDisconnecting,
  isWalletConnect,
  preparing,
  supportedChainsForConnectedAccount,
  waitingForWalletConfirmation,
} = storeToRefs(walletStore);
const { useQueryingBalances, warnUntrackedAddress } = useBalanceQueries(connected, connectedAddress);

const {
  amount,
  amountExceeded,
  asset,
  assetBalance,
  assetChain,
  estimatingGas,
  isNativeAsset,
  max,
  refreshAssetBalance,
  resetInput,
  showNeverInteractedWarning,
  switchToSelectedChain,
  toAddress,
  valid,
  wrongNetwork,
} = useTradeSendForm({
  chainOptions: supportedChainsForConnectedAccount,
  connectedAddress,
});

const { availableProviders, isDetecting: detectingProviders, showProviderSelection } = useUnifiedProviders();

const isConnecting = logicOr(preparing, detectingProviders);

const {
  clearError,
  connect,
  disconnect,
  errorMessage,
  selectProvider,
  send: sendTransaction,
  toggleConnection,
} = useTradeWalletActions();

const isWalletConnected = computed<boolean>(() => get(connected) && !!get(connectedAddress));

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
</script>

<template>
  <RuiCard
    class="rounded-xl!"
    no-padding
  >
    <TradeSendHeader
      :wallet-connected="isWalletConnected"
      :warn-untracked-address="warnUntrackedAddress"
      :querying-balances="useQueryingBalances"
      :loading="isConnecting"
      @connect="connect()"
      @disconnect="disconnect()"
    />
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
        class="w-full!"
        data-testid="track-action"
        @click="trackAddress()"
      >
        {{ t('trade.actions.track') }}
      </RuiButton>
      <RuiButton
        v-else-if="wrongNetwork"
        color="primary"
        size="lg"
        class="w-full!"
        data-testid="switch-network-action"
        @click="switchToSelectedChain()"
      >
        {{ t('trade.actions.change_network') }}
      </RuiButton>
      <RuiButton
        v-else
        color="primary"
        size="lg"
        class="w-full!"
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

  <ProviderSelectionDialog
    v-model="showProviderSelection"
    :providers="availableProviders"
    :loading="detectingProviders"
    @select-provider="selectProvider($event)"
  />
</template>
