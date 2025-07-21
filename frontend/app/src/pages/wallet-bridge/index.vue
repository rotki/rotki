<script setup lang="ts">
import type { EIP1193Provider } from '@/types';
import ConnectionLogs from '@/modules/onchain/wallet-bridge/ConnectionLogs.vue';
import ElectronConnectionStatus from '@/modules/onchain/wallet-bridge/ElectronConnectionStatus.vue';
import { useWalletBridgeWebSocket } from '@/modules/onchain/wallet-bridge/use-wallet-bridge-websocket';
import WalletAddressIndicator from '@/modules/onchain/wallet-bridge/WalletAddressIndicator.vue';
import { useMainStore } from '@/store/main';
import { logger } from '@/utils/logging';

interface LogEntry {
  message: string;
  timestamp: string;
  type: 'info' | 'success' | 'error';
}

definePage({
  meta: {
    layout: 'plain',
    title: 'rotki browser wallet bridge',
  },
});

defineOptions({
  name: 'WalletBridge',
});

const logs = ref<LogEntry[]>([]);
const showTakeoverMessage = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

// WebSocket integration
const {
  cleanup,
  cleanupWalletEventListeners,
  connect: connectToElectron,
  disconnect: disconnectFromElectron,
  isConnected: isElectronConnected,
  isConnecting: isElectronConnecting,
  lastError,
  onNotification,
  onRequest,
  sendResponse,
  setupWalletEventListeners,
} = useWalletBridgeWebSocket();

function addLog(message: string, type: 'info' | 'success' | 'error' = 'info'): void {
  const timestamp = new Date().toLocaleTimeString();
  logs.value = [{ message, timestamp, type }, ...logs.value];
}

function handleRetryConnection(): void {
  addLog('Retrying connection to Electron app...', 'info');
  connectToElectron();
}

function handleDisconnect(): void {
  disconnectFromElectron();
}

// Handle requests from Electron app
onRequest(async (message) => {
  try {
    // Get the browser wallet provider (MetaMask, etc.) that has the request method
    const provider: EIP1193Provider | undefined = window.ethereum;

    if (!provider) {
      throw new Error('No browser wallet provider found');
    }

    // Forward the request to the browser wallet
    const result = await provider.request<unknown>({
      method: message.method,
      params: message.params || [],
    });

    // Send successful response back to Electron
    sendResponse({
      id: message.id,
      jsonrpc: '2.0',
      result,
    });
  }
  catch (error: unknown) {
    logger.debug('Error handling request', error);
    const err = error as Error & { code?: number; data?: unknown };
    // Send error response back to Electron
    sendResponse({
      error: {
        code: err.code || -32603,
        data: err.data,
        message: err.message || 'Internal error',
      },
      id: message.id,
      jsonrpc: '2.0',
    });
  }
});

// Handle notifications from WebSocket
onNotification((notification) => {
  if (notification.type === 'reconnected') {
    // Show full-screen takeover message
    set(showTakeoverMessage, true);
    addLog('Another bridge is now active', 'error');
  }
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
    // Setup wallet event listeners when connected
    setupWalletEventListeners();
  }
  else if (!newValue && oldValue) {
    addLog('WebSocket connection to Electron app lost', 'error');
    // Cleanup wallet event listeners when disconnected
    cleanupWalletEventListeners();
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
      <div class="bg-rui-grey-100 dark:bg-rui-grey-800 p-8 rounded-lg shadow-2xl max-w-md mx-4 text-center border border-rui-grey-300 dark:border-rui-grey-600">
        <div>
          <RuiIcon
            name="lu-triangle-alert"
            class="text-rui-warning text-6xl mb-4"
          />
          <h2 class="text-h4 mb-2 text-rui-grey-900 dark:text-rui-grey-100 font-semibold">
            {{ t('trade.bridge.takeover.title') }}
          </h2>
          <p class="text-rui-grey-700 dark:text-rui-grey-300">
            {{ t('trade.bridge.takeover.description') }}
          </p>
        </div>
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
