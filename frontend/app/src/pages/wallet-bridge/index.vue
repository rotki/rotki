<script setup lang="ts">
import ConnectionLogs from '@/modules/onchain/wallet-bridge/ConnectionLogs.vue';
import ElectronConnectionStatus from '@/modules/onchain/wallet-bridge/ElectronConnectionStatus.vue';
import { useBridgeLogging } from '@/modules/onchain/wallet-bridge/use-bridge-logging';
import { useWalletProxyClient } from '@/modules/onchain/wallet-bridge/use-wallet-proxy-client';
import WalletAddressIndicator from '@/modules/onchain/wallet-bridge/WalletAddressIndicator.vue';
import { useMainStore } from '@/store/main';

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

// Logging
const { addLog, logs } = useBridgeLogging();

// WebSocket integration
const {
  cleanup,
  connect: connectToElectron,
  disconnect: disconnectFromElectron,
  isConnected: isElectronConnected,
  isConnecting: isElectronConnecting,
  lastError,
  onTakeOver,
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

// Cleanup on unmount
onBeforeUnmount(() => {
  cleanup();
});

const { setConnected } = useMainStore();

// Watch for connection state changes to log them
watch(isElectronConnecting, (newValue, oldValue) => {
  if (newValue && !oldValue) {
    addLog('Attempting to connect to Electron app via WebSocket...', 'info');
  }
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
});
</script>

<template>
  <div class="overflow-auto w-full text-rui-text">
    <!-- Full-screen takeover message -->
    <div
      v-if="showTakeoverMessage"
      class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50"
    >
      <div class="bg-rui-grey-100 dark:bg-rui-grey-800 p-8 rounded-lg shadow-2xl max-w-md mx-4 flex flex-col items-center text-center">
        <RuiIcon
          name="lu-triangle-alert"
          size="40"
          class="text-rui-warning mb-4"
        />
        <h2 class="text-h4 mb-2 font-semibold">
          {{ t('trade.bridge.takeover.title') }}
        </h2>
        <p class="text-rui-text-secondary">
          {{ t('trade.bridge.takeover.description') }}
        </p>
      </div>
    </div>

    <!-- Main content -->
    <div class="container !max-w-lg py-6 min-h-screen">
      <h4 class="text-h4 mb-4">
        {{ t('trade.bridge.title') }}
      </h4>

      <WalletAddressIndicator />

      <ElectronConnectionStatus
        :is-connected="isElectronConnected"
        :is-connecting="isElectronConnecting"
        :error="lastError"
        :on-retry-connection="handleRetryConnection"
        :on-disconnect="handleDisconnect"
      />

      <ConnectionLogs :logs="logs" />
    </div>
  </div>
</template>
