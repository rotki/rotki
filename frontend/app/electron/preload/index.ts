import type { ApiUrls, Credentials, Interop, Listeners, TrayUpdate, WalletBridgeRequest } from '@shared/ipc';
import type { EIP1193EventName, EIP1193Provider, EIP1193ProviderEvents, RpcRequest, WalletBridgeApi } from '@/types';
import { IpcCommands } from '@electron/ipc-commands';
import { type LogLevel, LogLevel as LogLevelEnum } from '@shared/log-level';
import { checkIfDevelopment } from '@shared/utils';
import { contextBridge, ipcRenderer } from 'electron';

const isDevelopment = checkIfDevelopment();

// Helper function to log to file
function logToFile(level: LogLevel, message: string): void {
  if (typeof window !== 'undefined' && window.interop?.logToFile) {
    window.interop.logToFile(level, message);
  }
}

interface DebugSettings {
  persistStore: boolean;
}

let debugSettings: DebugSettings | undefined = isDevelopment ? ipcRenderer.sendSync(IpcCommands.SYNC_GET_DEBUG) : undefined;

if (isDevelopment) {
  ipcRenderer.on(IpcCommands.DEBUG_SETTINGS, (event, args) => {
    debugSettings = args;
  });
}

contextBridge.exposeInMainWorld('interop', {
  openUrl: async (url: string) => ipcRenderer.invoke(IpcCommands.INVOKE_OPEN_URL, url),
  closeApp: async () => ipcRenderer.invoke(IpcCommands.INVOKE_CLOSE_APP),
  openDirectory: async (title: string) => ipcRenderer.invoke(IpcCommands.INVOKE_OPEN_DIRECTORY, title),
  premiumUserLoggedIn: (premiumUser: boolean) => ipcRenderer.send(IpcCommands.PREMIUM_LOGIN, premiumUser),
  setListeners(listeners: Listeners): void {
    ipcRenderer.on('failed', (event, error, code) => {
      listeners.onError(error, code);
      ipcRenderer.send('ack', 1);
    });

    ipcRenderer.on(IpcCommands.REQUEST_RESTART, () => {
      listeners.onRestart();
    });

    ipcRenderer.on(IpcCommands.ABOUT, () => {
      listeners.onAbout();
    });

    ipcRenderer.on(IpcCommands.BACKEND_PROCESS_DETECTED, (_event, pids) => {
      listeners.onProcessDetected(pids);
    });

    const onOAuthCallback = listeners.onOAuthCallback;
    if (onOAuthCallback) {
      ipcRenderer.on('oauth-callback', (_event, oAuthResult) => {
        onOAuthCallback(oAuthResult);
      });
    }
  },
  debugSettings: isDevelopment ? (): DebugSettings | undefined => debugSettings : undefined,
  apiUrls: (): ApiUrls => ipcRenderer.sendSync(IpcCommands.SYNC_API_URL),
  metamaskImport: async () => ipcRenderer.invoke(IpcCommands.INVOKE_WALLET_IMPORT),
  openWalletConnectBridge: async () => ipcRenderer.invoke(IpcCommands.OPEN_WALLET_CONNECT_BRIDGE),
  restartBackend: async options => ipcRenderer.invoke(IpcCommands.INVOKE_SUBPROCESS_START, options),
  checkForUpdates: async () => ipcRenderer.invoke(IpcCommands.INVOKE_UPDATE_CHECK),
  downloadUpdate: async (progress) => {
    ipcRenderer.on(IpcCommands.DOWNLOAD_PROGRESS, (event, args) => {
      progress(args);
    });
    return ipcRenderer.invoke(IpcCommands.INVOKE_DOWNLOAD_UPDATE);
  },
  installUpdate: async () => ipcRenderer.invoke(IpcCommands.INVOKE_INSTALL_UPDATE),
  setSelectedTheme: async selectedTheme => ipcRenderer.invoke(IpcCommands.INVOKE_THEME, selectedTheme),
  version: async () => ipcRenderer.invoke(IpcCommands.INVOKE_VERSION),
  isMac: async () => ipcRenderer.invoke(IpcCommands.INVOKE_IS_MAC),
  openPath: async (path: string) => ipcRenderer.invoke(IpcCommands.INVOKE_OPEN_PATH, path),
  config: async (defaults: boolean) => ipcRenderer.invoke(IpcCommands.INVOKE_CONFIG, defaults),
  updateTray: (trayUpdate: TrayUpdate) => ipcRenderer.send(IpcCommands.TRAY_UPDATE, trayUpdate),
  logToFile: (level: LogLevel, message: string) => {
    ipcRenderer.send(IpcCommands.LOG_TO_FILE, level, message);
  },
  storePassword: async (credentials: Credentials) => ipcRenderer.invoke(IpcCommands.INVOKE_STORE_PASSWORD, credentials),
  getPassword: async (username: string) => ipcRenderer.invoke(IpcCommands.INVOKE_GET_PASSWORD, username),
  clearPassword: async () => ipcRenderer.invoke(IpcCommands.INVOKE_CLEAR_PASSWORD),
  walletBridgeRequest: async (request: WalletBridgeRequest) => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_REQUEST, request),
  walletBridgeConnect: async () => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_CONNECT),
  walletBridgeDisconnect: async () => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_DISCONNECT),
  walletBridgeHttpListening: async () => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_HTTP_LISTENING),
  walletBridgeWebSocketListening: async () => ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_WS_LISTENING),
  notifyUserLogout: () => ipcRenderer.send(IpcCommands.USER_LOGOUT),
} satisfies Interop);

// EIP1193Provider implementation for wallet bridge
// Use the types from the main types file
const eventListeners = new Map<EIP1193EventName, ((...args: any[]) => void)[]>();

// Track wallet bridge states separately
let walletBridgeEnabled = false; // User has chosen to enable the bridge
let walletBridgeConnected = false; // Bridge is actually connected and functional

const walletBridgeProvider: EIP1193Provider = {
  isRotkiBridge: true,

  get connected(): boolean {
    return walletBridgeEnabled && walletBridgeConnected;
  },

  request: async (request: RpcRequest) => {
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

  on: <K extends EIP1193EventName>(
    event: K,
    callback: (...args: EIP1193ProviderEvents[K]) => void,
  ) => {
    if (!eventListeners.has(event)) {
      eventListeners.set(event, []);

      // Set up IPC listener for this event type
      ipcRenderer.on(`WALLET_BRIDGE_EVENT_${event}`, (_, data) => {
        const listeners = eventListeners.get(event) || [];
        listeners.forEach(listener => listener(data));
      });
    }

    eventListeners.get(event)!.push(callback as (...args: any[]) => void);
  },

  removeListener: <K extends EIP1193EventName>(
    event: K,
    callback: (...args: EIP1193ProviderEvents[K]) => void,
  ) => {
    const listeners = eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback as (...args: any[]) => void);
      if (index !== -1) {
        listeners.splice(index, 1);
      }
    }
  },

  off: <K extends EIP1193EventName>(
    event: K,
    callback: (...args: EIP1193ProviderEvents[K]) => void,
  ) => {
    // Alias for removeListener to match standard interface
    if (walletBridgeProvider.removeListener) {
      walletBridgeProvider.removeListener(event, callback);
    }
  },
};

// Connection status type
type WalletBridgeConnectionStatus = 'connected' | 'disconnected' | 'reconnected';

// Listen for wallet bridge connection status events
ipcRenderer.on(IpcCommands.WALLET_BRIDGE_CONNECTION_STATUS, (_, status: WalletBridgeConnectionStatus) => {
  if (status === 'connected') {
    walletBridgeConnected = true;
    // Emit connect event only if bridge is enabled
    if (walletBridgeEnabled) {
      emitConnectEvent().catch((error) => {
        logToFile(LogLevelEnum.ERROR, `Failed to emit connect event: ${String(error)}`);
      });
    }
  }
  else if (status === 'disconnected') {
    walletBridgeConnected = false;

    // Emit disconnect event to any listeners
    const disconnectListeners = eventListeners.get('disconnect') || [];
    disconnectListeners.forEach(listener => listener());
  }
  else if (status === 'reconnected') {
    walletBridgeConnected = true;
    // Emit connect event and accountsChanged event only if bridge is enabled
    if (walletBridgeEnabled) {
      emitConnectEvent().catch((error) => {
        logToFile(LogLevelEnum.ERROR, `Failed to emit connect event on reconnect: ${String(error)}`);
      });
      emitAccountsChangedEvent().catch((error) => {
        logToFile(LogLevelEnum.ERROR, `Failed to emit accounts changed event: ${String(error)}`);
      });
    }
  }
});

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

// Helper function to emit connect events with current chain and account info
async function emitConnectEvent(): Promise<void> {
  const connectListeners = eventListeners.get('connect') || [];
  if (connectListeners.length > 0) {
    const chainId = await fetchChainId();
    connectListeners.forEach(listener => listener({ chainId }));
  }
}

// Helper function to emit accountsChanged events with current accounts
async function emitAccountsChangedEvent(): Promise<void> {
  const accountsChangedListeners = eventListeners.get('accountsChanged') || [];
  if (accountsChangedListeners.length > 0) {
    const accounts = await fetchAccounts();
    accountsChangedListeners.forEach(listener => listener(accounts));
  }
}

// Always inject the ethereum provider
contextBridge.exposeInMainWorld('ethereum', walletBridgeProvider);

async function enableWalletBridge() {
  try {
    const connected = await ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_CONNECT);
    walletBridgeEnabled = true; // Always set enabled to true when user chooses to enable

    if (connected) {
      walletBridgeConnected = true;
      // Emit connect event with real chain ID
      await emitConnectEvent();
    }
  }
  catch (error) {
    logToFile(LogLevelEnum.ERROR, `Failed to enable wallet bridge: ${String(error)}`);
  }
}

async function disableWalletBridge() {
  try {
    await ipcRenderer.invoke(IpcCommands.WALLET_BRIDGE_DISCONNECT);
    walletBridgeEnabled = false; // User no longer wants to use the bridge
    walletBridgeConnected = false; // Bridge is no longer connected

    // Emit disconnect event
    const disconnectListeners = eventListeners.get('disconnect') || [];
    disconnectListeners.forEach(listener => listener());
  }
  catch (error) {
    logToFile(LogLevelEnum.ERROR, `Failed to disable wallet bridge: ${String(error)}`);
  }
}

// Expose wallet bridge control functions
contextBridge.exposeInMainWorld('walletBridge', {
  enable: enableWalletBridge,
  disable: disableWalletBridge,
  isEnabled: () => walletBridgeEnabled,
} satisfies WalletBridgeApi);
