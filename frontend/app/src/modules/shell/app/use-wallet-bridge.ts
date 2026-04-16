interface UseWalletBridgeReturn {
  readonly isPackaged: boolean;
  openProxyPageInDefaultBrowser: () => Promise<void>;
  isProxyClientConnected: () => Promise<boolean>;
  isProxyClientReady: () => Promise<boolean>;
  isProxyHttpListening: () => Promise<boolean>;
  isProxyWebSocketListening: () => Promise<boolean>;
  proxyStopServers: () => Promise<void>;
}

const electronApp = !!window.interop;

const walletBridge: UseWalletBridgeReturn = {
  get isPackaged(): boolean {
    return electronApp;
  },

  isProxyClientConnected: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.isWalletBridgeClientConnected()) ?? false;
  },

  isProxyClientReady: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.isWalletBridgeClientReady()) ?? false;
  },

  isProxyHttpListening: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.isWalletBridgeHttpListening()) ?? false;
  },

  isProxyWebSocketListening: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.isWalletBridgeWebSocketListening()) ?? false;
  },

  openProxyPageInDefaultBrowser: async (): Promise<void> => {
    if (electronApp) {
      await window.walletBridge?.openWalletBridge();
    }
  },

  proxyStopServers: async (): Promise<void> => {
    if (electronApp && window.walletBridge) {
      await window.walletBridge.walletBridgeStopServers();
    }
  },
};

export const useWalletBridge = (): UseWalletBridgeReturn => walletBridge;
