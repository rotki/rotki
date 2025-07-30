import type { EIP6963ProviderDetail } from '@/types';
import { logger } from '@/utils/logging';
import { useProxyProvider } from '../wallet-bridge/use-proxy-provider';

/**
 * Detects providers available through the wallet bridge
 */
export async function detectProxyProviders(): Promise<EIP6963ProviderDetail[]> {
  const walletBridge = window.walletBridge;
  if (!walletBridge) {
    return [];
  }

  try {
    // Get available providers from the bridge
    const bridgeProviders = await walletBridge.getAvailableProviders();

    // Create a proxy provider to be used with bridge providers
    const proxyProvider = useProxyProvider();

    if (!proxyProvider) {
      logger.warn('Failed to create proxy provider for bridge providers');
      return bridgeProviders;
    }

    // Enhance bridge providers with the proxy provider
    // Since bridge providers come serialized without the provider object,
    // we use the proxy provider for all of them
    return bridgeProviders.map(providerDetail => ({
      ...providerDetail,
      provider: proxyProvider,
    }));
  }
  catch (error) {
    logger.error('Failed to detect bridge providers:', error);
    return [];
  }
}
