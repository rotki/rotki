import type { EnhancedProviderDetail } from '@/modules/onchain/wallet-providers/provider-detection';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { logger } from '@/modules/common/logging/logging';
import { useInjectedWallet } from '@/modules/onchain/wallet-bridge/use-injected-wallet';
import { isUserRejectedError } from '@/modules/onchain/wallet-constants';
import { useUnifiedProviders } from '@/modules/onchain/wallet-providers/use-unified-providers';

interface UseProviderSelectionReturn {
  handleProviderSelection: (provider: EnhancedProviderDetail, onError: (message: string) => void) => Promise<void>;
}

export function useProviderSelection(): UseProviderSelectionReturn {
  const injectedWallet = useInjectedWallet();
  const unifiedProviders = useUnifiedProviders();

  async function handleProviderSelection(
    provider: EnhancedProviderDetail,
    onError: (message: string) => void,
  ): Promise<void> {
    try {
      await unifiedProviders.selectProvider(provider.info.uuid);
      await injectedWallet.connectToSelectedProvider();
    }
    catch (error: unknown) {
      if (isUserRejectedError(error)) {
        onError('Wallet connection was rejected by user');
      }
      else {
        const message = getErrorMessage(error);
        if (message.includes('Request timeout')) {
          onError('Connection request timed out. Please try again.');
        }
        else {
          onError(`Failed to connect wallet: ${message}`);
        }
      }
      logger.error('Provider selection failed:', error);
    }
  }

  return { handleProviderSelection };
}
