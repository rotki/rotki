import type { EIP1193Provider, EIP6963ProviderDetail, EIP6963ProviderInfo } from '@/types';
import { createSharedComposable, get, set, useSessionStorage } from '@vueuse/core';
import { readonly, ref, type Ref, watch } from 'vue';
import { logger } from '@/utils/logging';

export interface EIP6963ProvidersComposable {
  availableProviders: EIP6963ProviderDetail[];
  getAvailableProviders: (options?: DetectProvidersOptions) => Promise<EIP6963ProviderDetail[]>;
  getSelectedProvider: () => EIP1193Provider | undefined;
  hasSelectedProvider: Ref<boolean>;
  isDetecting: Ref<boolean>;
  selectProvider: (uuid: string) => boolean;
  selectedProviderMetadata: Readonly<Ref<EIP6963ProviderInfo | undefined>>;
  selectedProviderUuid: Ref<string | undefined>;
  onProviderChanged: (callback: (provider: EIP1193Provider | undefined) => void) => () => void;
}

interface DetectProvidersOptions {
  maxRetries?: number;
  retryDelay?: number;
  timeout?: number;
}

function createEIP6963ProvidersComposable(): EIP6963ProvidersComposable {
  // Only persist the selected provider UUID to avoid serialization issues
  const selectedProviderUuid = useSessionStorage<string | undefined>('rotki:bridge:selectedProvider', undefined);

  let selectedProvider: EIP1193Provider | undefined;
  let availableProviders: EIP6963ProviderDetail[] = [];
  const isDetecting = ref<boolean>(false);
  const providerMap = new Map<string, EIP1193Provider>();
  const detectedProviderUuids = new Set<string>();

  const providerChangeListeners = new Set<(provider: EIP1193Provider | undefined) => void>();

  // Helper to notify listeners when provider changes
  const notifyProviderChanged = (newProvider: EIP1193Provider | undefined): void => {
    providerChangeListeners.forEach((callback) => {
      try {
        callback(newProvider);
      }
      catch (error) {
        logger.error('[EIP-6963] Error in provider change listener:', error);
      }
    });
  };

  logger.info('[EIP-6963] useEIP6963Providers composable initialized');

  const detectProvidersOnce = async (timeout: number): Promise<EIP6963ProviderDetail[]> => new Promise((resolve) => {
    const providers: EIP6963ProviderDetail[] = [];
    logger.debug(`[EIP-6963] Starting single detection attempt with timeout: ${timeout}ms`);

    // Listen for provider announcements
    const handleProviderAnnounce = (event: any): void => {
      logger.debug('[EIP-6963] Received eip6963:announceProvider event', event);
      const { detail } = event;
      if (detail?.info && detail?.provider) {
        const { uuid } = detail.info;

        // Skip if we already have this provider
        if (detectedProviderUuids.has(uuid)) {
          logger.debug(`[EIP-6963] Provider ${detail.info.name} (${uuid}) already detected, skipping`);
          return;
        }

        const providerDetail: EIP6963ProviderDetail = {
          info: {
            icon: detail.info.icon,
            name: detail.info.name,
            rdns: detail.info.rdns,
            uuid,
          },
          // Use a placeholder for serialization - actual provider stored separately
          provider: {} as any,
        };
        providers.push(providerDetail);
        providerMap.set(uuid, detail.provider);

        logger.info(`[EIP-6963] Detected new provider: ${detail.info.name} (${uuid})`);

        // If this is the selected provider UUID and we don't have a provider set, set it now
        const currentSelectedUuid = get(selectedProviderUuid);
        if (currentSelectedUuid === uuid && !selectedProvider) {
          selectedProvider = detail.provider;
          logger.info(`[EIP-6963] Automatically restored selected provider: ${detail.info.name} (${uuid})`);
          notifyProviderChanged(selectedProvider);
        }
      }
      else {
        logger.warn('[EIP-6963] Invalid provider announcement event', event);
      }
    };

    window.addEventListener('eip6963:announceProvider', handleProviderAnnounce);
    logger.debug('[EIP-6963] Added event listener for provider announcements');

    // Request providers to announce themselves
    logger.debug('[EIP-6963] Dispatching eip6963:requestProvider event');
    window.dispatchEvent(new Event('eip6963:requestProvider'));

    // Set up timeout
    setTimeout(() => {
      window.removeEventListener('eip6963:announceProvider', handleProviderAnnounce);
      logger.debug(`[EIP-6963] Detection timeout reached, found ${providers.length} provider(s)`);
      resolve(providers);
    }, timeout);
  });

  const selectProvider = (uuid: string): boolean => {
    // Handle clearing provider selection
    if (uuid === '') {
      set(selectedProviderUuid, undefined);
      selectedProvider = undefined;
      logger.info('[EIP-6963] Cleared provider selection');
      notifyProviderChanged(undefined);
      return true;
    }

    const providerDetail = availableProviders.find(p => p.info.uuid === uuid);
    const actualProvider = providerMap.get(uuid);

    if (providerDetail) {
      set(selectedProviderUuid, uuid);

      if (actualProvider) {
        selectedProvider = actualProvider;
        logger.info(`[EIP-6963] Selected provider: ${providerDetail.info.name} (${uuid})`);
        notifyProviderChanged(selectedProvider);
      }
      else {
        // Clear selectedProvider if we don't have the actual provider in memory
        selectedProvider = undefined;
        logger.info(`[EIP-6963] Provider ${uuid} not in memory, will be restored when detected`);
        notifyProviderChanged(undefined);
      }
      return true;
    }
    return false;
  };

  const getAvailableProviders = async (options: DetectProvidersOptions = {}): Promise<EIP6963ProviderDetail[]> => {
    logger.debug('[EIP-6963] getAvailableProviders called - checking if detection needed');

    // If we already have providers and we're not forcing a refresh, return cached results
    const cachedProviders = get(availableProviders);
    if (cachedProviders.length > 0 && !get(isDetecting)) {
      logger.debug(`[EIP-6963] Returning ${cachedProviders.length} cached provider(s)`);
      return cachedProviders;
    }

    // Otherwise, detect and return providers
    return detectAndGetProviders(options);
  };

  const getSelectedProvider = (): EIP1193Provider | undefined => {
    logger.debug(`[EIP-6963] getSelectedProvider called`, selectedProvider);
    if (!selectedProvider) {
      logger.warn(`[EIP-6963] Selected provider not found`);
    }
    return selectedProvider;
  };

  const detectAndGetProviders = async (options: DetectProvidersOptions = {}): Promise<EIP6963ProviderDetail[]> => {
    logger.info('[EIP-6963] detectAndGetProviders called - unified detection and fetch');

    const {
      maxRetries = 3,
      retryDelay = 500,
      timeout = 300,
    } = options;

    set(isDetecting, true);

    try {
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        logger.info(`[EIP-6963] Provider detection attempt ${attempt + 1}/${maxRetries + 1}`);

        const providers = await detectProvidersOnce(timeout);

        // If we found new providers, update the list
        if (providers.length > 0) {
          const currentProviders = get(availableProviders);
          const updatedProviders = [...currentProviders];

          // Add only new providers that weren't already detected
          for (const provider of providers) {
            if (!detectedProviderUuids.has(provider.info.uuid)) {
              updatedProviders.push(provider);
              detectedProviderUuids.add(provider.info.uuid);
            }
          }

          availableProviders = updatedProviders;
          logger.info(`[EIP-6963] Detected ${providers.length} new provider(s). Total: ${updatedProviders.length}`);
        }

        // If this isn't the last attempt and we haven't found any providers yet, wait before retrying
        if (attempt < maxRetries && get(availableProviders).length === 0) {
          logger.debug(`[EIP-6963] No providers found yet. Waiting ${retryDelay}ms before retry...`);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
        }
      }

      const finalProviders = get(availableProviders);
      if (finalProviders.length === 0) {
        logger.warn('[EIP-6963] No providers detected after all retries');
      }
      else {
        logger.info(`[EIP-6963] Detection complete. Found ${finalProviders.length} provider(s):`, finalProviders.map(p => p.info.name));
      }

      // After detection, try to restore selected provider if needed
      if (get(selectedProviderUuid) && !selectedProvider) {
        const storedUuid = get(selectedProviderUuid);
        const actualProvider = providerMap.get(storedUuid!);
        if (actualProvider) {
          selectedProvider = actualProvider;
          logger.info(`[EIP-6963] Restored selected provider: ${storedUuid}`);
          notifyProviderChanged(selectedProvider);
        }
      }

      return finalProviders;
    }
    catch (error) {
      logger.error('[EIP-6963] Failed to detect and get providers:', error);
      // Return cached providers on error
      return get(availableProviders);
    }
    finally {
      set(isDetecting, false);
    }
  };

  // Ref to store metadata for the selected provider (updated via events)
  const selectedProviderMetadata = ref<EIP6963ProviderInfo | undefined>();

  // Update metadata when UUID changes
  const updateProviderMetadata = (): void => {
    const uuid = get(selectedProviderUuid);
    if (!uuid) {
      set(selectedProviderMetadata, undefined);
      return;
    }

    const providerDetail = availableProviders.find(p => p.info.uuid === uuid);
    set(selectedProviderMetadata, providerDetail ? providerDetail.info : undefined);
  };

  // Watch for UUID changes to update metadata
  watch(selectedProviderUuid, updateProviderMetadata, { immediate: true });

  // Reactive boolean for whether a provider is selected
  const hasSelectedProvider = ref<boolean>(!!selectedProvider);

  // Update hasSelectedProvider when provider changes
  const updateHasSelectedProvider = (provider: EIP1193Provider | undefined): void => {
    set(hasSelectedProvider, !!provider);
  };

  // Add internal listener to update hasSelectedProvider
  providerChangeListeners.add(updateHasSelectedProvider);

  // Initialize hasSelectedProvider
  updateHasSelectedProvider(selectedProvider);

  // Event listener registration function
  const onProviderChanged = (callback: (provider: EIP1193Provider | undefined) => void): (() => void) => {
    providerChangeListeners.add(callback);
    // Return cleanup function
    return () => {
      providerChangeListeners.delete(callback);
    };
  };

  return {
    availableProviders: availableProviders as any,
    getAvailableProviders,
    getSelectedProvider,
    hasSelectedProvider,
    isDetecting,
    onProviderChanged,
    selectedProviderMetadata: readonly(selectedProviderMetadata),
    selectedProviderUuid,
    selectProvider,
  };
}

// Export as shared composable to maintain state across components
export const useEIP6963Providers = createSharedComposable(createEIP6963ProvidersComposable);
