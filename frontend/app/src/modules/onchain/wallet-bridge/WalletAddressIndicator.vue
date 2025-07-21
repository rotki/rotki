<script setup lang="ts">
import type { EIP1193Provider } from '@/types';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useMainStore } from '@/store/main';
import { logger } from '@/utils/logging';

const { t } = useI18n({ useScope: 'global' });
const { getChainFromChainId } = useWalletHelper();
const { setConnected } = useMainStore();

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

async function updateWalletInfo(): Promise<void> {
  try {
    const provider: EIP1193Provider | undefined = window.ethereum;

    if (!provider) {
      set(connectedAddress, undefined);
      set(connectedChainId, undefined);
      return;
    }

    // Get connected accounts
    const accounts = await provider.request({ method: 'eth_accounts' }) as string[];
    if (accounts.length > 0) {
      set(connectedAddress, accounts[0]);
    }
    else {
      set(connectedAddress, undefined);
    }

    // Get chain ID
    const chainId = await provider.request({ method: 'eth_chainId' }) as string;
    set(connectedChainId, parseInt(chainId, 16));
  }
  catch (error) {
    logger.error('Error getting wallet info:', error);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  }
}

async function connectWallet(): Promise<void> {
  try {
    set(isConnecting, true);
    set(connectionError, undefined);
    const provider: EIP1193Provider | undefined = window.ethereum;

    if (!provider) {
      throw new Error('No wallet provider found. Please install a wallet extension like MetaMask.');
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
  catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to connect wallet';
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
  const provider: EIP1193Provider | undefined = window.ethereum;

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

// Update wallet info on mount
onMounted(() => {
  updateWalletInfo();
  setConnected(true);
  const provider: EIP1193Provider | undefined = window.ethereum;

  if (provider === undefined) {
    return;
  }

  const handleAccountsChanged = (accounts: string[]) => {
    if (accounts.length > 0) {
      set(connectedAddress, accounts[0]);
    }
    else {
      set(connectedAddress, undefined);
    }
  };

  const handleChainChanged = (chainId: string) => {
    set(connectedChainId, parseInt(chainId, 16));
  };

  provider.on?.('accountsChanged', handleAccountsChanged);
  provider.on?.('chainChanged', handleChainChanged);

  onBeforeUnmount(() => {
    provider.removeListener?.('accountsChanged', handleAccountsChanged);
    provider.removeListener?.('chainChanged', handleChainChanged);
  });
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
      <template v-else>
        <div class="p-0.5 rounded-full size-3 border border-rui-grey-400/40">
          <div class="size-full rounded-full bg-rui-grey-400" />
        </div>
        <span class="text-rui-text-secondary flex-1">
          {{ t('trade.bridge.no_wallet_connected') }}
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
    </div>

    <!-- Connection Error Display -->
    <div
      v-if="connectionError"
      class="mt-2 p-2 rounded-md bg-rui-error/10 border border-rui-error/20"
    >
      <div class="flex items-start gap-2">
        <RuiIcon
          name="alert-triangle-line"
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
            name="close-line"
            size="14"
          />
        </RuiButton>
      </div>
    </div>
  </div>
</template>
