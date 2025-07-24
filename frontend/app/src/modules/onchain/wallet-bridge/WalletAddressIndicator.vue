<script setup lang="ts">
import type { EIP1193Provider } from '@/types';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useMainStore } from '@/store/main';
import { logger } from '@/utils/logging';
import { useEIP6963Providers } from './use-eip6963-providers';

const { t } = useI18n({ useScope: 'global' });
const { getChainFromChainId } = useWalletHelper();
const { setConnected } = useMainStore();
const { getSelectedProvider, hasSelectedProvider, selectedProviderMetadata } = useEIP6963Providers();

const connectedAddress = ref<string>();
const connectedChainId = ref<number>();

const chain = computed(() => {
  const chainId = get(connectedChainId);
  if (!chainId) {
    return undefined;
  }
  return getChainFromChainId(chainId);
});

const isConnected = computed<boolean>(() => !!get(connectedAddress));
const isConnecting = ref<boolean>(false);
const connectionError = ref<string>();

async function connectWallet(): Promise<void> {
  try {
    set(isConnecting, true);
    set(connectionError, undefined);
    const provider: EIP1193Provider | undefined = getSelectedProvider();

    if (!provider) {
      throw new Error('No wallet provider found. Please select a wallet provider first.');
    }

    // Request account access
    const accounts = await provider.request<string[]>({ method: 'eth_requestAccounts' });
    if (accounts.length > 0) {
      set(connectedAddress, accounts[0]);

      // Get chain ID after connecting
      const chainId = await provider.request<string>({ method: 'eth_chainId' });
      set(connectedChainId, parseInt(chainId, 16));

      logger.info('Wallet connected successfully:', accounts[0]);
    }
    else {
      throw new Error('No accounts returned from wallet.');
    }
  }
  catch (error: any) {
    const errorMessage = 'message' in error ? error.message : 'Failed to connect wallet';
    logger.error('Error connecting wallet:', error);
    set(connectionError, errorMessage);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  }
  finally {
    set(isConnecting, false);
  }
}

async function disconnectProvider() {
  const provider: EIP1193Provider | undefined = getSelectedProvider();

  if (provider) {
    // Some wallets support disconnect method
    if (provider.disconnect) {
      try {
        await provider.disconnect();
      }
      catch (error) {
        // Some wallets don't support disconnect, which is fine
        logger.debug('Wallet disconnect method not supported or failed:', error);
      }
    }

    // For wallets that don't support disconnect, we can request permissions revocation
    // This is not universally supported but works for some wallets
    try {
      await provider.request({
        method: 'wallet_revokePermissions',
        params: [{ eth_accounts: {} }],
      });
    }
    catch (error) {
      // This method is not supported by all wallets
      logger.debug('wallet_revokePermissions not supported:', error);
    }
  }
}

async function disconnectWallet(): Promise<void> {
  try {
    await disconnectProvider();

    // Clear the connected state
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
    set(connectionError, undefined);

    logger.info('Wallet disconnected');
  }
  catch (error) {
    logger.error('Error disconnecting wallet:', error);
    // Still clear the state even if disconnect fails
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
    set(connectionError, undefined);
  }
}

function resetError(): void {
  set(connectionError, undefined);
}

// Track current provider and its event listeners
let currentProvider: EIP1193Provider | undefined;
let accountsChangedListener: ((accounts: string[]) => void) | undefined;
let chainChangedListener: ((chainId: string) => void) | undefined;

function handleAccountsChanged(accounts: string[]): void {
  if (accounts.length > 0) {
    set(connectedAddress, accounts[0]);
  }
  else {
    set(connectedAddress, undefined);
  }
}

function handleChainChanged(chainId: string): void {
  set(connectedChainId, parseInt(chainId, 16));
}

function setupProviderListeners(provider: EIP1193Provider): void {
  if (!provider.on) {
    return;
  }

  // Store listener references for cleanup
  accountsChangedListener = handleAccountsChanged;
  chainChangedListener = handleChainChanged;

  provider.on('accountsChanged', accountsChangedListener);
  provider.on('chainChanged', chainChangedListener);
  logger.info('Set up event listeners for provider');
}

function cleanupProviderListeners(): void {
  if (currentProvider?.removeListener && accountsChangedListener && chainChangedListener) {
    currentProvider.removeListener('accountsChanged', accountsChangedListener);
    currentProvider.removeListener('chainChanged', chainChangedListener);
    logger.info('Cleaned up event listeners for provider');
  }
  currentProvider = undefined;
  accountsChangedListener = undefined;
  chainChangedListener = undefined;
}

// Use event system to watch for provider changes
const { onProviderChanged } = useEIP6963Providers();
const unsubscribeProviderChange = onProviderChanged((newProvider) => {
  logger.info('Selected provider changed:', {
    new: newProvider ? 'provider set' : 'no provider',
    old: currentProvider ? 'provider set' : 'no provider',
  });

  // Clean up old provider listeners
  if (currentProvider && currentProvider !== newProvider) {
    cleanupProviderListeners();
  }

  // Set up new provider
  if (newProvider) {
    currentProvider = newProvider;
    setupProviderListeners(newProvider);
    // Clear state - we'll only update from events
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  }
  else {
    // Clear wallet info when no provider
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  }
});

// Initialize with current provider
const initialProvider = getSelectedProvider();
if (initialProvider) {
  currentProvider = initialProvider;
  setupProviderListeners(initialProvider);
}

// Set connected state on mount (no RPC calls)
onMounted(() => {
  setConnected(true);
});

onBeforeUnmount(() => {
  cleanupProviderListeners();
  unsubscribeProviderChange();
});
</script>

<template>
  <div class="mb-4">
    <div class="flex items-center gap-3 mb-2">
      <h5 class="font-bold">
        {{ t('trade.bridge.wallet_status') }}
      </h5>
    </div>

    <div class="border border-default rounded-md px-3 py-2 flex items-center gap-2 font-mono text-sm font-medium bg-rui-grey-50 dark:bg-rui-grey-900">
      <template v-if="isConnected">
        <div class="p-0.5 rounded-full size-3 border border-rui-success-lighter/40">
          <div class="size-full rounded-full bg-rui-success-lighter" />
        </div>
        <img
          v-if="selectedProviderMetadata"
          :src="selectedProviderMetadata.icon"
          :alt="selectedProviderMetadata.name"
          class="w-4 h-4"
        />
        <ChainIcon
          v-if="chain"
          :chain="chain"
          size="14px"
        />
        <HashLink
          v-if="connectedAddress"
          class="!pl-0 flex-1"
          :location="chain"
          :text="connectedAddress"
          copy-only
        />
        <RuiButton
          variant="outlined"
          color="error"
          size="sm"
          @click="disconnectWallet()"
        >
          {{ t('trade.bridge.disconnect') }}
        </RuiButton>
      </template>
      <template v-else-if="hasSelectedProvider">
        <div class="p-0.5 rounded-full size-3 border border-rui-warning/40">
          <div class="size-full rounded-full bg-rui-warning" />
        </div>
        <img
          v-if="selectedProviderMetadata"
          :src="selectedProviderMetadata.icon"
          :alt="selectedProviderMetadata.name"
          class="w-4 h-4"
        />
        <span class="text-rui-text-secondary flex-1">
          {{ t('trade.bridge.provider_not_connected', { provider: selectedProviderMetadata?.name }) }}
        </span>
        <RuiButton
          variant="outlined"
          color="primary"
          size="sm"
          :loading="isConnecting"
          @click="connectWallet()"
        >
          {{ t('trade.bridge.connect_wallet') }}
        </RuiButton>
      </template>
      <template v-else>
        <div class="p-0.5 rounded-full size-3 border border-rui-grey-400/40">
          <div class="size-full rounded-full bg-rui-grey-400" />
        </div>
        <span class="text-rui-text-secondary flex-1">
          {{ t('trade.bridge.no_provider_selected') }}
        </span>
      </template>
    </div>

    <!-- Connection Error Display -->
    <div
      v-if="connectionError"
      class="mt-2 p-2 rounded-md bg-rui-error/10 border border-rui-error/20"
    >
      <div class="flex items-start gap-2">
        <RuiIcon
          name="lu-triangle-alert"
          class="text-rui-error mt-0.5"
          size="16"
        />
        <div class="flex-1">
          <p class="text-sm text-rui-error font-medium mb-1">
            {{ t('trade.bridge.connection_failed') }}
          </p>
          <p class="text-xs text-rui-error/80">
            {{ connectionError }}
          </p>
        </div>
        <RuiButton
          variant="text"
          size="sm"
          :icon="true"
          @click="resetError()"
        >
          <RuiIcon
            name="lu-x"
            size="14"
          />
        </RuiButton>
      </div>
    </div>
  </div>
</template>
