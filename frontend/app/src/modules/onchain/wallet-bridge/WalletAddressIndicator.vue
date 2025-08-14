<script setup lang="ts">
import type { EIP1193Provider } from '@/types';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useMainStore } from '@/store/main';
import { useUnifiedProviders } from '../wallet-providers/use-unified-providers';
import ProviderIcon from './ProviderIcon.vue';
import StatusDot from './StatusDot.vue';
import { useWalletConnection } from './use-wallet-connection';
import { useWalletConnectionState } from './use-wallet-connection-state';

const { t } = useI18n({ useScope: 'global' });

const { setConnected } = useMainStore();

const { getChainFromChainId } = useWalletHelper();
const { activeProvider, hasSelectedProvider, onProviderChanged, selectedProviderMetadata } = useUnifiedProviders();
const { isRequestingAccounts } = useWalletConnectionState();
const {
  cleanupProviderListeners,
  clearProvider,
  connectedAddress,
  connectedChainId,
  connectionError,
  connectToProvider,
  disconnectFromProvider,
  isConnecting,
  resetError,
  setupProvider,
} = useWalletConnection();

const getSelectedProvider = (): EIP1193Provider | undefined => get(activeProvider);

const isConnected = computed<boolean>(() => !!get(connectedAddress));

const chain = computed<string | undefined>(() => {
  const chainId = get(connectedChainId);
  if (!chainId) {
    return undefined;
  }
  return getChainFromChainId(chainId);
});

async function connectWallet(): Promise<void> {
  const provider: EIP1193Provider | undefined = getSelectedProvider();
  if (!provider) {
    return;
  }
  await connectToProvider(provider);
}

async function disconnectWallet(): Promise<void> {
  const provider: EIP1193Provider | undefined = getSelectedProvider();
  await disconnectFromProvider(provider);
}

const unsubscribeProviderChange = onProviderChanged((newProvider) => {
  if (newProvider) {
    setupProvider(newProvider);
  }
  else {
    clearProvider();
  }
});

onMounted(() => {
  setConnected(true);
  const initialProvider = getSelectedProvider();
  if (initialProvider) {
    setupProvider(initialProvider);
  }
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
        <StatusDot status="connected" />
        <ProviderIcon :metadata="selectedProviderMetadata" />
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
      <template v-else-if="hasSelectedProvider && isRequestingAccounts">
        <StatusDot
          status="connecting"
          animate
        />
        <ProviderIcon :metadata="selectedProviderMetadata" />
        <span class="text-rui-text-secondary flex-1">
          {{ t('trade.bridge.connecting_to_wallet', { provider: selectedProviderMetadata?.name }) }}
        </span>
        <RuiProgress
          color="primary"
          circular
          size="20"
          class="mr-1"
        />
      </template>
      <template v-else-if="hasSelectedProvider">
        <StatusDot status="warning" />
        <ProviderIcon :metadata="selectedProviderMetadata" />
        <span class="text-rui-text-secondary flex-1">
          {{ t('trade.bridge.provider_not_connected', { provider: selectedProviderMetadata?.name }) }}
        </span>
        <RuiButton
          variant="outlined"
          color="primary"
          size="sm"
          :loading="isConnecting || isRequestingAccounts"
          @click="connectWallet()"
        >
          {{ t('trade.bridge.connect_wallet') }}
        </RuiButton>
      </template>
      <template v-else>
        <StatusDot status="disconnected" />
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
