import type { EnhancedProviderDetail } from '@/modules/onchain/wallet-providers/provider-detection';
import { get, set } from '@vueuse/core';
import { computed } from 'vue';
import { useInterop } from '@/composables/electron-interop';
import { useBridgedWallet } from '@/modules/onchain/wallet-bridge/use-bridged-wallet';
import { useInjectedWallet } from '@/modules/onchain/wallet-bridge/use-injected-wallet';
import { useUnifiedProviders } from '@/modules/onchain/wallet-providers/use-unified-providers';
import { logger } from '@/utils/logging';

export interface WalletConnectionComposable {
  initiateConnection: () => Promise<void>;
  selectProvider: (provider: EnhancedProviderDetail) => Promise<void>;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
}

export function useWalletConnection(): WalletConnectionComposable {
  const walletProviders = useUnifiedProviders();
  const { isPackaged } = useInterop();
  const { setupBridge } = useBridgedWallet();
  const injectedWallet = useInjectedWallet();

  // Provider store state
  const availableProviders = computed<EnhancedProviderDetail[]>(() => get(walletProviders.availableProviders));

  // Check if bridge has a selected provider
  const checkBridgeSelectedProvider = async (): Promise<boolean> => {
    try {
      if (!get(isPackaged) || !window.walletBridge) {
        return false;
      }

      const selectedProvider = await window.walletBridge.getSelectedProvider();
      return selectedProvider !== null;
    }
    catch (error) {
      logger.debug('Failed to check bridge selected provider:', error);
      return false;
    }
  };

  const hasSelectedProvider = async (): Promise<boolean> => {
    if (isPackaged) {
      return checkBridgeSelectedProvider();
    }
    else {
      return get(walletProviders.hasSelectedProvider);
    }
  };

  const initiateConnection = async (): Promise<void> => {
    try {
      // Note: isDetecting is readonly in unified providers

      if (get(isPackaged)) {
        await setupBridge();
      }

      const providerSelected = await hasSelectedProvider();

      if (!providerSelected) {
        await walletProviders.detectProviders();
        const providers = get(availableProviders);

        if (providers.length === 0) {
          throw new Error('No wallet providers detected');
        }
        else if (providers.length === 1) {
          const provider = providers[0];
          await walletProviders.selectProvider(provider.info.uuid);
          await injectedWallet.connectToSelectedProvider();
        }
        else {
          set(walletProviders.showProviderSelection, true);
        }
      }
      else {
        await injectedWallet.connectToSelectedProvider();
      }
    }
    catch (error) {
      console.error('Failed to initiate wallet connection:', error);
      throw error;
    }
    finally {
      // Note: isDetecting is readonly in unified providers
    }
  };

  const selectProvider = async (provider: EnhancedProviderDetail): Promise<void> => {
    try {
      await walletProviders.selectProvider(provider.info.uuid);
    }
    catch (error) {
      console.error('Failed to select provider:', error);
      walletProviders.clearProvider();
    }
  };

  const connect = async (): Promise<void> => {
    try {
      // Connect to the selected provider (bridge already setup)
      await injectedWallet.connectToSelectedProvider();
    }
    catch (error) {
      console.error('Failed to connect to selected provider:', error);
      throw error;
    }
  };

  const disconnect = async (): Promise<void> => {
    await injectedWallet.disconnect();
    walletProviders.clearProvider();
  };

  return {
    connect,
    disconnect,
    initiateConnection,
    selectProvider,
  };
}
