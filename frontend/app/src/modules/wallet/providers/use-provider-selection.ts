import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useInjectedWallet } from '@/modules/wallet/bridge/use-injected-wallet';
import { isUserRejectedError } from '@/modules/wallet/constants';
import { useUnifiedProviders } from '@/modules/wallet/providers/use-unified-providers';

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
