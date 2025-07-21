import type { WalletBridgeRequest } from '@shared/ipc';
import type { WalletBridgeApi } from '@/types';
import { IpcCommands } from '@electron/ipc-commands';
import { type LogLevel, LogLevel as LogLevelEnum } from '@shared/log-level';
import { contextBridge, ipcRenderer } from 'electron';

// Helper function to log to file
function logToFile(level: LogLevel, message: string): void {
  ipcRenderer.send(IpcCommands.LOG_TO_FILE, level, message);
}

// Track wallet bridge states
let walletBridgeEnabled = false;
let walletBridgeConnected = false;

// Event forwarding for wallet bridge events
const walletEventCallbacks = new Map<string, (data: any) => void>();
let walletEventIpcSetup = false;

// Connection status type
type WalletBridgeConnectionStatus = 'connected' | 'disconnected' | 'reconnected';

// Helper function to fetch chain ID from bridge
async function fetchChainId(): Promise<string> {
  try {
    const response = await ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_REQUEST, {
      method: 'eth_chainId',
      params: [],
    });
    return response.result ?? '0x1';
  }
  catch (error) {
    logToFile(LogLevelEnum.WARNING, `Failed to fetch chain ID from bridge: ${String(error)}`);
    return '0x1'; // Fallback to mainnet
  }
}

// Helper function to fetch accounts from bridge
async function fetchAccounts(): Promise<string[]> {
  try {
    const response = await ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_REQUEST, {
      method: 'eth_accounts',
      params: [],
    });
    return response.result ?? [];
  }
  catch (error) {
    logToFile(LogLevelEnum.WARNING, `Failed to fetch accounts from bridge: ${String(error)}`);
    return [];
  }
}

async function enableWalletBridge(): Promise<void> {
  try {
    const connected = await ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_CONNECT);
    walletBridgeEnabled = true;

    if (connected) {
      walletBridgeConnected = true;
    }
  }
  catch (error) {
    logToFile(LogLevelEnum.ERROR, `Failed to enable wallet bridge: ${String(error)}`);
  }
}

async function disableWalletBridge(): Promise<void> {
  try {
    await ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_DISCONNECT);
    walletBridgeEnabled = false;
    walletBridgeConnected = false;
  }
  catch (error) {
    logToFile(LogLevelEnum.ERROR, `Failed to disable wallet bridge: ${String(error)}`);
  }
}

// Set up wallet event forwarding from main process
function setupWalletEventForwarding(): void {
  if (!walletEventIpcSetup) {
    ipcRenderer.on('WALLET_BRIDGE_EVENT', (_, { eventName, eventData }) => {
      const callback = walletEventCallbacks.get(eventName);
      if (callback) {
        callback(eventData);
      }
    });
    walletEventIpcSetup = true;
  }
}

// Set up connection status listener
function setupConnectionStatusListener(): void {
  // Listen for wallet bridge connection status events
  ipcRenderer.on(IpcCommands.WALLET_BRIDGE_CONNECTION_STATUS, (_, status: WalletBridgeConnectionStatus) => {
    if (status === 'connected') {
      walletBridgeConnected = true;
      const connectCallback = walletEventCallbacks.get('connect');
      if (walletBridgeEnabled && connectCallback) {
        // Fetch initial chain and emit connect event
        fetchChainId()
          .then(chainId => connectCallback({ chainId }))
          .catch(error => logToFile(LogLevelEnum.ERROR, `Failed to emit connect event: ${String(error)}`));
      }
    }
    else if (status === 'disconnected') {
      walletBridgeConnected = false;
      const disconnectCallback = walletEventCallbacks.get('disconnect');
      if (disconnectCallback) {
        disconnectCallback({});
      }
    }
    else if (status === 'reconnected') {
      walletBridgeConnected = true;
      if (walletBridgeEnabled) {
        const connectCallback = walletEventCallbacks.get('connect');
        const accountsChangedCallback = walletEventCallbacks.get('accountsChanged');

        if (connectCallback) {
          fetchChainId()
            .then(chainId => connectCallback({ chainId }))
            .catch(error => logToFile(LogLevelEnum.ERROR, `Failed to emit connect event: ${String(error)}`));
        }

        if (accountsChangedCallback) {
          fetchAccounts()
            .then(accounts => accountsChangedCallback(accounts))
            .catch(error => logToFile(LogLevelEnum.ERROR, `Failed to emit accounts changed event: ${String(error)}`));
        }
      }
    }
  });
}

// Initialize wallet bridge
export function initializeWalletBridge(): void {
  setupConnectionStatusListener();

  // Expose enhanced wallet bridge API
  contextBridge.exposeInMainWorld('walletBridge', {
    // Connection management
    enable: enableWalletBridge,
    disable: disableWalletBridge,
    isEnabled: () => walletBridgeEnabled,
    isConnected: () => walletBridgeConnected,

    // Bridge server management
    openWalletBridge: async () => ipcRenderer.invoke(IpcCommands.OPEN_WALLET_CONNECT_BRIDGE),
    walletBridgeConnect: async () => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_CONNECT),
    walletBridgeHttpListening: async () => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_HTTP_LISTENING),
    walletBridgeWebSocketListening: async () => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_WS_LISTENING),

    // RPC requests
    request: async (request: WalletBridgeRequest) => {
      if (!walletBridgeEnabled) {
        throw new Error('Wallet bridge is not enabled. Please connect your wallet first.');
      }

      if (!walletBridgeConnected) {
        throw new Error('Wallet bridge is not connected. Please check your connection and try again.');
      }

      const response = await ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_REQUEST, {
        method: request.method,
        params: request.params ?? [],
      });

      if (response.error) {
        const error = new Error(response.error.message);
        (error as any).code = response.error.code;
        (error as any).data = response.error.data;
        throw error;
      }

      return response.result;
    },

    // Event management
    addEventListener: (eventName: string, callback: (data: any) => void) => {
      setupWalletEventForwarding();
      walletEventCallbacks.set(eventName, callback);
    },

    removeEventListener: (eventName: string) => {
      walletEventCallbacks.delete(eventName);
    },
  } satisfies WalletBridgeApi);
}
