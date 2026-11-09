<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useMainStore } from '@/modules/core/common/use-main-store';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';
import { CLIENT_CONFIG } from '@/modules/wallet/bridge/bridge-config';
import BridgeOverlay from '@/modules/wallet/bridge/BridgeOverlay.vue';
import ConnectionLogs from '@/modules/wallet/bridge/ConnectionLogs.vue';
import ElectronConnectionStatus from '@/modules/wallet/bridge/ElectronConnectionStatus.vue';
import ProviderSelectionNotification from '@/modules/wallet/bridge/ProviderSelectionNotification.vue';
import { useBridgeLogging } from '@/modules/wallet/bridge/use-bridge-logging';
import { BridgeConnectionPhase, useWalletProxyClient } from '@/modules/wallet/bridge/use-wallet-proxy-client';
import WalletAddressIndicator from '@/modules/wallet/bridge/WalletAddressIndicator.vue';

definePage({
  meta: {
    layout: 'plain',
    title: 'rotki browser wallet bridge',
  },
});

defineOptions({
  name: 'WalletBridge',
});

const showTakeoverMessage = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();

const { addLog, logs } = useBridgeLogging();

const {
  cleanup,
  connect: connectToElectron,
  disconnect: disconnectFromElectron,
  isConnected: isElectronConnected,
  lastError,
  onTakeOver,
  state: connectionState,
} = useWalletProxyClient();

function handleRetryConnection(): void {
  addLog('Retrying connection to Electron app...', 'info');
  connectToElectron();
}

function handleDisconnect(): void {
  disconnectFromElectron();
}

onTakeOver(() => {
  set(showTakeoverMessage, true);
  addLog('Another bridge is now active', 'error');
});

onBeforeUnmount(() => {
  cleanup();
});

const { setConnected } = useMainStore();

// Watch for connection state changes to log them
watch(connectionState, (state) => {
  if (state.phase !== BridgeConnectionPhase.connecting)
    return;
  addLog(
    state.attempt === 0
      ? 'Attempting to connect to Electron app via WebSocket...'
      : `Reconnecting to Electron app (attempt ${state.attempt + 1} of ${CLIENT_CONFIG.MAX_RETRIES})...`,
    'info',
  );
});

watch(isElectronConnected, (newValue, oldValue) => {
  if (newValue && !oldValue) {
    addLog('Successfully connected to Electron app!', 'success');
  }
  else if (!newValue && oldValue) {
    addLog('WebSocket connection to Electron app lost', 'error');
  }
});

onBeforeMount(() => {
  setConnected(true);
  connectToElectron();
  if (import.meta.env.DEV && route.query.mockWallets) {
    startPromise(import('@/modules/wallet/bridge/dev-mock-wallets').then(({ installMockWallets }) => {
      installMockWallets({
        count: Number(route.query.mockWallets),
        rejects: route.query.mockWalletsReject !== undefined,
      });
    }));
  }
});
</script>

<template>
  <div class="overflow-auto w-full text-rui-text">
    <BridgeOverlay
      v-if="showTakeoverMessage"
      color="warning"
      icon="lu-triangle-alert"
      :title="t('trade.bridge.takeover.title')"
      :description="t('trade.bridge.takeover.description')"
    />

    <ProviderSelectionNotification />

    <div class="container max-w-lg! min-h-screen py-8 flex flex-col gap-6">
      <header class="flex items-center gap-3">
        <RotkiLogo
          size="2"
          unique-key="wallet-bridge"
        />
        <h1 class="text-h5 font-medium">
          {{ t('trade.bridge.title') }}
        </h1>
      </header>

      <RuiAlert
        type="warning"
        variant="default"
      >
        {{ t('trade.bridge.keep_tab_active') }}
      </RuiAlert>

      <WalletAddressIndicator />

      <ElectronConnectionStatus
        :state="connectionState"
        :error="lastError"
        :on-retry-connection="handleRetryConnection"
        :on-disconnect="handleDisconnect"
      />

      <ConnectionLogs :logs="logs" />
    </div>
  </div>
</template>
