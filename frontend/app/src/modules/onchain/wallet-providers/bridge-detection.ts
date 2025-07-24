import type { EIP6963ProviderDetail } from '@/types';
import { logger } from '@/utils/logging';

/**
 * Detects providers available through the wallet bridge
 */
export async function detectBridgeProviders(): Promise<EIP6963ProviderDetail[]> {
  const walletBridge = window.walletBridge;
  if (!walletBridge) {
    return [];
  }

  try {
    // Single method that detects and returns providers
    return await walletBridge.getAvailableProviders();
  }
  catch (error) {
    logger.error('Failed to detect bridge providers:', error);
    return [];
  }
}
