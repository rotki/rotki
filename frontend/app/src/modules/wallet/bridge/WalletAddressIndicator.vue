<script setup lang="ts">
import type { EIP1193Provider } from '@/types';
import { useMainStore } from '@/modules/core/common/use-main-store';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { useWalletHelper } from '@/modules/wallet/use-wallet-helper';
import { useUnifiedProviders } from '../providers/use-unified-providers';
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
  <RuiCard divide>
    <template #header>
      {{ t('trade.bridge.wallet_status') }}
    </template>

    <div class="flex items-center gap-3 min-h-9 text-sm">
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
          class="pl-0! flex-1 font-mono"
          :location="chain"
          :text="connectedAddress"
          display-mode="copy"
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

    <div
      v-if="connectionError"
      class="mt-4"
    >
      <RuiAlert
        type="error"
        :title="t('trade.bridge.connection_failed')"
        closeable
        @close="resetError()"
      >
        {{ connectionError }}
      </RuiAlert>
    </div>
  </RuiCard>
</template>
