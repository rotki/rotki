import type { EIP1193Provider, EIP6963AnnounceProviderEvent, EIP6963ProviderDetail } from '@/types';
import { assert } from '@rotki/common';
import { uniqueObjects } from '@/utils/data';
import { logger } from '@/utils/logging';
import { useProxyProvider } from '../wallet-bridge/use-proxy-provider';

export interface ProviderDetectionOptions {
  includeLegacy?: boolean;
  timeout?: number;
}

export interface EnhancedProviderDetail extends EIP6963ProviderDetail {
  source: 'eip6963' | 'legacy' | 'bridge';
  isConnected?: boolean;
  lastSeen?: number;
}

/**
 * Detects EIP-6963 compliant wallet providers
 */
async function detectEIP6963Providers(timeout: number = 1000): Promise<EnhancedProviderDetail[]> {
  return new Promise((resolve) => {
    const providers: EnhancedProviderDetail[] = [];

    function handleProviderAnnouncement(event: EIP6963AnnounceProviderEvent): void {
      providers.push({
        ...event.detail,
        lastSeen: Date.now(),
        source: 'eip6963',
      });
    }

    function cleanup(): void {
      window.removeEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    }

    window.addEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    window.dispatchEvent(new Event('eip6963:requestProvider'));

    setTimeout(() => {
      cleanup();
      resolve(uniqueObjects(providers, item => item.info.uuid));
    }, timeout);
  });
}

/**
 * Detects legacy wallet providers (window.ethereum without EIP-6963)
 */
async function detectLegacyProviders(): Promise<EnhancedProviderDetail[]> {
  const providers: EnhancedProviderDetail[] = [];

  if (typeof window !== 'undefined' && window.ethereum) {
    // Check if this provider already announced via EIP-6963
    const isEIP6963Provider = window.ethereum.isRotkiBridge ||
      (await detectEIP6963Providers(100)).length > 0;

    if (!isEIP6963Provider) {
      // Create a legacy provider detail
      providers.push({
        info: {
          icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96"><circle cx="48" cy="48" r="48" fill="%23f6851b"/><text x="48" y="52" text-anchor="middle" font-size="24" fill="white">W</text></svg>',
          name: 'Legacy Wallet',
          rdns: 'legacy.wallet.provider',
          uuid: 'legacy-wallet-provider',
        },
        lastSeen: Date.now(),
        provider: window.ethereum,
        source: 'legacy',
      });
    }
  }

  return providers;
}

/**
 * Detects environment type
 */
function detectEnvironment(): 'browser' | 'electron' {
  if (typeof window !== 'undefined' && window.walletBridge) {
    return 'electron';
  }
  return 'browser';
}

/**
 * Detects providers available through the wallet bridge
 */
async function detectProxyProviders(): Promise<EIP6963ProviderDetail[]> {
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

/**
 * Enhanced wallet provider detection - auto-detects environment
 */
export async function getAllWalletProviders(
  options: ProviderDetectionOptions = {},
): Promise<EnhancedProviderDetail[]> {
  const {
    includeLegacy = true,
    timeout = 2000,
  } = options;

  const isElectron = detectEnvironment() === 'electron';
  const providers: EnhancedProviderDetail[] = [];

  try {
    // Add bridge providers if in Electron environment
    if (isElectron) {
      const bridgeProviders = await detectProxyProviders();
      bridgeProviders.forEach((bridgeProvider) => {
        providers.push({
          ...bridgeProvider,
          lastSeen: Date.now(),
          source: 'bridge',
        });
      });
    }
    else {
      // Always detect EIP-6963 providers
      const eip6963Providers = await detectEIP6963Providers(timeout);
      providers.push(...eip6963Providers);

      // Add legacy providers if requested and no EIP-6963 providers found
      if (includeLegacy && eip6963Providers.length === 0) {
        const legacyProviders = await detectLegacyProviders();
        providers.push(...legacyProviders);
      }
    }

    return uniqueObjects(providers, item => item.info.uuid);
  }
  catch (error) {
    console.error('Error detecting wallet providers:', error);
    return [];
  }
}

/**
 * @deprecated Use getAllWalletProviders instead
 * Legacy function for backward compatibility with WalletImportSelection
 */
export async function getAllBrowserWalletProviders(): Promise<EIP6963ProviderDetail[]> {
  return getAllWalletProviders({ includeLegacy: true });
}

/**
 * Get addresses from a wallet provider
 */
export async function getAddressesFromWallet(provider: EIP1193Provider): Promise<string[]> {
  try {
    assert(provider, 'Provider is required');

    // Request account access
    return await provider.request<string[]>({
      method: 'eth_requestAccounts',
    });
  }
  catch (error) {
    logger.error('Failed to get addresses from wallet:', error);
    throw new Error(`Failed to connect to wallet: ${String(error)}`);
  }
}
