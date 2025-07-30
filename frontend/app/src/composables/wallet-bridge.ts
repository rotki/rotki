interface UseWalletBridgeReturn {
  readonly isPackaged: boolean;
  openProxyPageInDefaultBrowser: () => Promise<void>;
  proxyConnect: () => Promise<boolean>;
  proxyHttpListening: () => Promise<boolean>;
  proxyWebSocketListening: () => Promise<boolean>;
  proxyClientReady: () => Promise<boolean>;
}

const electronApp = !!window.interop;

const walletBridge: UseWalletBridgeReturn = {
  get isPackaged(): boolean {
    return electronApp;
  },

  openProxyPageInDefaultBrowser: async (): Promise<void> => {
    if (electronApp) {
      await window.walletBridge?.openWalletBridge();
    }
  },

  proxyClientReady: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.walletBridgeClientReady()) ?? false;
  },

  proxyConnect: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.walletBridgeConnect()) ?? false;
  },

  proxyHttpListening: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.walletBridgeHttpListening()) ?? false;
  },

  proxyWebSocketListening: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.walletBridgeWebSocketListening()) ?? false;
  },
};

export const useWalletBridge = (): UseWalletBridgeReturn => walletBridge;
