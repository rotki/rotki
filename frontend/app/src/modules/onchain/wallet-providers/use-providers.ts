import type { EIP1193Provider } from '@/types';
import { createSharedComposable, useLocalStorage } from '@vueuse/core';
import { type ComputedRef, ref, type Ref } from 'vue';
import { logger } from '@/utils/logging';
import { type EnhancedProviderDetail, getAllWalletProviders, type ProviderDetectionOptions } from './provider-detection';

interface ProviderPreferences {
  lastSelectedUuid?: string;
  autoSelectSingle: boolean;
  preferredSource?: 'eip6963' | 'legacy' | 'bridge';
}

interface UseProvidersReturn {
  activeProvider: ComputedRef<EIP1193Provider | undefined>;
  cleanup: () => void;
  clearProvider: () => void;
  detectionError: Ref<string | undefined>;
  detectProviders: (options?: ProviderDetectionOptions) => Promise<void>;
  detectingProviders: Ref<boolean>;
  getProviderByUuid: (uuid: string) => (EnhancedProviderDetail | undefined);
  hasAnyProvider: ComputedRef<boolean>;
  hasMultipleProviders: ComputedRef<boolean>;
  initialize: () => void;
  isDetecting: Ref<boolean>;
  preferences: Readonly<Ref<ProviderPreferences>>;
  providers: Readonly<Ref<EnhancedProviderDetail[]>>;
  providersBySource: ComputedRef<{
    bridge: EnhancedProviderDetail[];
    eip6963: EnhancedProviderDetail[];
    legacy: EnhancedProviderDetail[];
  }>;
  refreshProviders: () => Promise<void>;
  selectedProvider: Readonly<Ref<EnhancedProviderDetail | undefined>>;
  selectProvider: (uuid: string) => Promise<void>;
  showProviderSelection: Ref<boolean>;
  updateConnectionStatus: () => Promise<void>;
}

function _useProviders(): UseProvidersReturn {
  // Reactive state
  const providers = ref<EnhancedProviderDetail[]>([]);
  const selectedProvider = ref<EnhancedProviderDetail>();
  const isDetecting = ref<boolean>(false);
  const detectionError = ref<string>();
  const showProviderSelection = ref<boolean>(false);
  const detectingProviders = ref<boolean>(false);

  // Provider preferences - automatically persisted to localStorage
  const preferences = useLocalStorage<ProviderPreferences>('rotki-provider-preferences', {
    autoSelectSingle: true,
    preferredSource: 'eip6963',
  });

  // Computed properties
  const hasMultipleProviders = computed<boolean>(() => get(providers).length > 1);
  const hasAnyProvider = computed<boolean>(() => get(providers).length > 0);
  const activeProvider = computed<EIP1193Provider | undefined>(() => get(selectedProvider)?.provider);

  // Get providers grouped by source
  const providersBySource = computed(() => {
    const groups = {
      bridge: [] as EnhancedProviderDetail[],
      eip6963: [] as EnhancedProviderDetail[],
      legacy: [] as EnhancedProviderDetail[],
    };

    get(providers).forEach((provider) => {
      groups[provider.source].push(provider);
    });

    return groups;
  });

  // Detect available providers
  async function detectProviders(options: ProviderDetectionOptions = {}): Promise<void> {
    set(isDetecting, true);
    set(detectionError, undefined);

    try {
      logger.debug('Starting provider detection with options:', options);

      const detectedProviders = await getAllWalletProviders(options);
      set(providers, detectedProviders);

      logger.debug(`Detected ${detectedProviders.length} providers in ${window.walletBridge ? 'electron' : 'browser'} mode`);

      // Auto-select if preferences allow and conditions are met
      await handleAutoSelection();
    }
    catch (error: any) {
      logger.error('Provider detection failed:', error);
      set(detectionError, error.message || 'Failed to detect providers');
      set(providers, []);
    }
    finally {
      set(isDetecting, false);
    }
  }

  // Handle automatic provider selection
  async function handleAutoSelection(): Promise<void> {
    const currentProviders = get(providers);
    const prefs = get(preferences);

    if (!prefs.autoSelectSingle || currentProviders.length === 0) {
      return;
    }

    // Auto-select single provider
    if (currentProviders.length === 1) {
      await selectProvider(currentProviders[0].info.uuid);
      return;
    }

    // Try to select previously used provider
    if (prefs.lastSelectedUuid) {
      const previousProvider = currentProviders.find(p => p.info.uuid === prefs.lastSelectedUuid);
      if (previousProvider) {
        await selectProvider(previousProvider.info.uuid);
        return;
      }
    }

    // Select preferred source if available
    if (prefs.preferredSource) {
      const preferredProviders = currentProviders.filter(p => p.source === prefs.preferredSource);
      if (preferredProviders.length === 1) {
        await selectProvider(preferredProviders[0].info.uuid);
      }
    }
  }

  // Select a specific provider
  async function selectProvider(uuid: string): Promise<void> {
    const provider = get(providers).find(p => p.info.uuid === uuid);

    if (!provider) {
      throw new Error(`Provider with UUID ${uuid} not found`);
    }

    logger.debug('Selecting provider:', provider.info.name);

    set(showProviderSelection, false);
    set(selectedProvider, provider);

    // Update preferences (automatically persisted by useLocalStorage)
    set(preferences, {
      ...get(preferences),
      lastSelectedUuid: uuid,
    });

    // If this is a bridge provider, notify the bridge
    if (provider.source === 'bridge' && window.walletBridge?.selectProvider) {
      try {
        await window.walletBridge.selectProvider(uuid);
      }
      catch (error) {
        logger.error('Failed to notify bridge of provider selection:', error);
      }
    }
  }

  function clearProvider(): void {
    set(showProviderSelection, false);
    set(selectedProvider, undefined);

    set(preferences, {
      ...get(preferences),
      lastSelectedUuid: undefined,
    });
  }

  // Refresh providers (re-detect)
  async function refreshProviders(): Promise<void> {
    await detectProviders({
      includeLegacy: true,
      timeout: 2000,
    });
  }

  // Get provider by UUID
  function getProviderByUuid(uuid: string): EnhancedProviderDetail | undefined {
    return get(providers).find(p => p.info.uuid === uuid);
  }

  // Check if a provider is connected
  async function checkProviderConnection(provider: EnhancedProviderDetail): Promise<boolean> {
    try {
      if (provider.provider.connected !== undefined) {
        return provider.provider.connected;
      }

      // Try to get accounts without requesting permission
      const accounts = await provider.provider.request<string[]>({ method: 'eth_accounts' });
      return accounts.length > 0;
    }
    catch {
      return false;
    }
  }

  // Update connection status for all providers
  async function updateConnectionStatus(): Promise<void> {
    const currentProviders = get(providers);
    const updatedProviders = await Promise.all(
      currentProviders.map(async (provider) => {
        const isConnected = await checkProviderConnection(provider);
        return {
          ...provider,
          isConnected,
          lastSeen: Date.now(),
        };
      }),
    );

    set(providers, updatedProviders);
  }

  // Initialize the store
  function initialize(): void {
    // Auto-detect providers on initialization
    detectProviders().catch((error) => {
      logger.error('Initial provider detection failed:', error);
    });
  }

  // Cleanup function
  function cleanup(): void {
    set(providers, []);
    set(selectedProvider, undefined);
    set(isDetecting, false);
    set(detectionError, undefined);
    set(showProviderSelection, false);
    set(detectingProviders, false);
  }

  return {
    activeProvider,
    cleanup,
    clearProvider,
    detectingProviders,
    detectionError: readonly(detectionError),
    detectProviders,
    getProviderByUuid,
    hasAnyProvider,
    hasMultipleProviders,
    initialize,
    isDetecting: readonly(isDetecting),
    preferences: readonly(preferences),
    providers: readonly(providers) as Readonly<Ref<EnhancedProviderDetail[]>>,
    providersBySource,
    refreshProviders,
    selectedProvider: readonly(selectedProvider),
    selectProvider,
    showProviderSelection,
    updateConnectionStatus,
  };
}

// Export as shared composable to ensure single instance across app
export const useProviders = createSharedComposable(_useProviders);
