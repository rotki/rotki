interface UseWalletBridgeReturn {
  readonly isPackaged: boolean;
  openWalletBridge: () => Promise<void>;
  walletBridgeConnect: () => Promise<boolean>;
  walletBridgeHttpListening: () => Promise<boolean>;
  walletBridgeWebSocketListening: () => Promise<boolean>;
}

const electronApp = !!window.interop;

const walletBridge: UseWalletBridgeReturn = {
  get isPackaged(): boolean {
    return electronApp;
  },

  openWalletBridge: async (): Promise<void> => {
    if (electronApp) {
      await window.walletBridge?.openWalletBridge();
    }
  },

  walletBridgeConnect: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.walletBridgeConnect()) ?? false;
  },

  walletBridgeHttpListening: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.walletBridgeHttpListening()) ?? false;
  },

  walletBridgeWebSocketListening: async (): Promise<boolean> => {
    if (!electronApp || !window.walletBridge)
      return false;
    return (await window.walletBridge.walletBridgeWebSocketListening()) ?? false;
  },
};

export const useWalletBridge = (): UseWalletBridgeReturn => walletBridge;
