import type { EIP1193Provider, EIP6963ProviderInfo } from '@/types';
import { createSharedComposable, get, set, useLocalStorage } from '@vueuse/core';
import { computed, type ComputedRef, readonly, ref, type Ref } from 'vue';
import { logger } from '@/utils/logging';
import { type EnhancedProviderDetail, getAllWalletProviders, type ProviderDetectionOptions } from './provider-detection';

// Simplified provider preferences (removed manual source selection)
interface ProviderPreferences {
  lastSelectedUuid?: string;
  autoSelectSingle: boolean;
}

// Extended options for detection
interface UnifiedDetectionOptions extends ProviderDetectionOptions {
  maxRetries?: number;
  retryDelay?: number;
}

type OnProviderChangedCallback = (provider: EIP1193Provider | undefined, oldProvider: EIP1193Provider | undefined) => void;

// Comprehensive return interface combining both systems
interface UnifiedProvidersComposable {
  // Core provider data
  availableProviders: Readonly<Ref<EnhancedProviderDetail[]>>;
  selectedProvider: Readonly<Ref<EnhancedProviderDetail | undefined>>;
  selectedProviderUuid: Readonly<Ref<string | undefined>>;

  // Provider access
  activeProvider: ComputedRef<EIP1193Provider | undefined>;
  selectedProviderMetadata: ComputedRef<EIP6963ProviderInfo | undefined>;

  // State flags
  isDetecting: Readonly<Ref<boolean>>;
  hasSelectedProvider: ComputedRef<boolean>;

  // UI state
  showProviderSelection: Ref<boolean>;

  // Actions
  detectProviders: (options?: UnifiedDetectionOptions) => Promise<EnhancedProviderDetail[]>;
  selectProvider: (uuid: string) => Promise<boolean>;
  clearProvider: () => void;
  checkIfSelectedProvider: () => Promise<boolean>;

  // Event system
  onProviderChanged: (callback: OnProviderChangedCallback) => () => void;

  // Lifecycle
  initialize: () => void;
  cleanup: () => void;
}

function createUnifiedProvidersComposable(): UnifiedProvidersComposable {
  // Reactive state - using localStorage for consistency and persistence
  const availableProviders = ref<EnhancedProviderDetail[]>([]);
  const selectedProvider = ref<EnhancedProviderDetail>();
  const isDetecting = ref<boolean>(false);
  const detectionError = ref<string>();

  // UI state
  const showProviderSelection = ref<boolean>(false);

  // Simplified provider preferences - no manual source selection
  const preferences = useLocalStorage<ProviderPreferences>('rotki-provider-preferences', {
    autoSelectSingle: true,
  });

  // Provider change listeners (from EIP6963 system)
  const providerChangeListeners = new Set<OnProviderChangedCallback>();

  // Internal provider map for quick access (from EIP6963 system)
  const providerMap = new Map<string, EIP1193Provider>();

  // Environment detection
  const isElectronMode = computed<boolean>(() => !!window.walletBridge);

  // Computed properties
  const selectedProviderUuid = computed<string | undefined>(() => get(selectedProvider)?.info.uuid);
  const activeProvider = computed<EIP1193Provider | undefined>(() => get(selectedProvider)?.provider);
  const selectedProviderMetadata = computed<EIP6963ProviderInfo | undefined>(() => get(selectedProvider)?.info);
  const hasSelectedProvider = computed<boolean>(() => !!get(selectedProvider));

  // Check if provider is selected (includes bridge check for Electron mode)
  const checkIfSelectedProvider = async (): Promise<boolean> => {
    if (get(isElectronMode)) {
      try {
        if (!window.walletBridge) {
          return false;
        }
        const bridgeProvider = await window.walletBridge.getSelectedProvider();
        return bridgeProvider !== null;
      }
      catch (error) {
        logger.debug('[UnifiedProviders] Failed to check bridge selected provider:', error);
        return false;
      }
    }
    else {
      return get(hasSelectedProvider);
    }
  };

  // Helper to notify provider change listeners
  const notifyProviderChanged = (newProvider: EIP1193Provider | undefined, oldProvider: EIP1193Provider | undefined): void => {
    providerChangeListeners.forEach((callback) => {
      try {
        callback(newProvider, oldProvider);
      }
      catch (error) {
        logger.error('[UnifiedProviders] Error in provider change listener:', error);
      }
    });
  };

  // Detect available providers with retry logic (combining both approaches)
  async function detectProviders(options: UnifiedDetectionOptions = {}): Promise<EnhancedProviderDetail[]> {
    const {
      includeLegacy = true,
      maxRetries = 3,
      retryDelay = 500,
      timeout = 2000,
    } = options;

    set(isDetecting, true);
    set(detectionError, undefined);

    try {
      logger.debug('[UnifiedProviders] Starting provider detection with options:', options);
      logger.debug(`[UnifiedProviders] Environment: ${get(isElectronMode) ? 'Electron' : 'Browser'} mode`);

      let detectedProviders: EnhancedProviderDetail[] = [];

      // Retry logic for detection (from EIP6963 system)
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        logger.debug(`[UnifiedProviders] Detection attempt ${attempt + 1}/${maxRetries + 1}`);

        try {
          detectedProviders = await getAllWalletProviders({ includeLegacy, timeout });

          if (detectedProviders.length > 0) {
            break; // Success, no need to retry
          }
        }
        catch (error) {
          logger.warn(`[UnifiedProviders] Detection attempt ${attempt + 1} failed:`, error);

          if (attempt === maxRetries) {
            throw error; // Last attempt, propagate error
          }
        }

        // Wait before retry (except on last attempt)
        if (attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, retryDelay));
        }
      }

      // Update provider map for quick access
      providerMap.clear();
      detectedProviders.forEach((provider) => {
        providerMap.set(provider.info.uuid, provider.provider);
      });

      set(availableProviders, detectedProviders);

      const sourceBreakdown = detectedProviders.reduce((acc, p) => {
        acc[p.source] = (acc[p.source] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      logger.info(`[UnifiedProviders] Detected ${detectedProviders.length} providers:`, sourceBreakdown);

      // Auto-select based on preferences and detected source
      await handleAutoSelection();

      return detectedProviders;
    }
    catch (error: any) {
      logger.error('[UnifiedProviders] Provider detection failed:', error);
      set(detectionError, error.message || 'Failed to detect providers');
      set(availableProviders, []);
      return [];
    }
    finally {
      set(isDetecting, false);
    }
  }

  // Handle automatic provider selection with smart source preference
  async function handleAutoSelection(): Promise<void> {
    const currentProviders = get(availableProviders);
    const prefs = get(preferences);

    if (!prefs.autoSelectSingle || currentProviders.length === 0) {
      return;
    }

    // Auto-select single provider regardless of source
    if (currentProviders.length === 1) {
      await selectProvider(currentProviders[0].info.uuid);
      return;
    }

    // Try to select previously used provider (if still available)
    if (prefs.lastSelectedUuid) {
      const previousProvider = currentProviders.find(p => p.info.uuid === prefs.lastSelectedUuid);
      if (previousProvider) {
        logger.debug(`[UnifiedProviders] Restoring previously selected provider: ${previousProvider.info.name}`);
        await selectProvider(previousProvider.info.uuid);
        return;
      }
    }

    // Auto-select based on environment and source priority
    await handleSmartAutoSelection(currentProviders);
  }

  // Handle smart auto-selection based on environment and source priority
  async function handleSmartAutoSelection(providers: EnhancedProviderDetail[]): Promise<void> {
    // In Electron mode with walletBridge, prefer bridge providers
    if (get(isElectronMode)) {
      const bridgeProviders = providers.filter(p => p.source === 'bridge');
      if (bridgeProviders.length === 1) {
        logger.debug(`[UnifiedProviders] Auto-selecting single bridge provider: ${bridgeProviders[0].info.name}`);
        await selectProvider(bridgeProviders[0].info.uuid);
        return;
      }
      if (bridgeProviders.length > 1) {
        logger.debug('[UnifiedProviders] Multiple bridge providers available, user selection required');
        set(showProviderSelection, true);
        return;
      }
    }

    // Priority order: eip6963 -> legacy (excluding bridge which was handled above)
    const priorityOrder: Array<'eip6963' | 'legacy'> = ['eip6963', 'legacy'];

    for (const source of priorityOrder) {
      const sourceProviders = providers.filter(p => p.source === source);
      if (sourceProviders.length === 1) {
        logger.debug(`[UnifiedProviders] Auto-selecting single ${source} provider: ${sourceProviders[0].info.name}`);
        await selectProvider(sourceProviders[0].info.uuid);
        return;
      }
    }

    logger.debug('[UnifiedProviders] No single provider available for auto-selection');
  }

  // Select a specific provider (combining both approaches)
  async function selectProvider(uuid: string): Promise<boolean> {
    // Handle clearing provider selection
    if (uuid === '') {
      clearProvider();
      return true;
    }

    const provider = get(availableProviders).find(p => p.info.uuid === uuid);

    if (!provider) {
      logger.error(`[UnifiedProviders] Provider with UUID ${uuid} not found`);
      return false;
    }

    logger.info(`[UnifiedProviders] Selecting ${provider.source} provider: ${provider.info.name} (${uuid})`);

    const oldProvider = get(selectedProvider)?.provider;
    set(selectedProvider, provider);

    // Update preferences (automatically persisted by useLocalStorage)
    set(preferences, {
      ...get(preferences),
      lastSelectedUuid: uuid,
    });

    // Notify change listeners
    notifyProviderChanged(provider.provider, oldProvider);

    // If this is a bridge provider, notify the bridge
    if (provider.source === 'bridge' && window.walletBridge?.selectProvider) {
      try {
        await window.walletBridge.selectProvider(uuid);
        logger.debug(`[UnifiedProviders] Notified bridge of provider selection: ${provider.info.name}`);
      }
      catch (error) {
        logger.error('[UnifiedProviders] Failed to notify bridge of provider selection:', error);
        return false;
      }
    }

    return true;
  }

  // Clear provider selection
  function clearProvider(): void {
    const previousProvider = get(selectedProvider);

    set(selectedProvider, undefined);

    // Update preferences
    set(preferences, {
      ...get(preferences),
      lastSelectedUuid: undefined,
    });

    // Notify change listeners
    notifyProviderChanged(undefined, previousProvider?.provider);

    if (previousProvider) {
      logger.info(`[UnifiedProviders] Cleared provider selection: ${previousProvider.info.name}`);
    }
  }

  // Event listener registration
  const onProviderChanged = (callback: OnProviderChangedCallback): (() => void) => {
    providerChangeListeners.add(callback);
    // Return cleanup function
    return () => {
      providerChangeListeners.delete(callback);
    };
  };

  // Initialize the composable
  function initialize(): void {
    logger.info(`[UnifiedProviders] Initializing in ${get(isElectronMode) ? 'Electron' : 'Browser'} mode`);

    // Auto-detect providers on initialization
    detectProviders().catch((error) => {
      logger.error('[UnifiedProviders] Initial provider detection failed:', error);
    });
  }

  // Cleanup function
  function cleanup(): void {
    set(availableProviders, []);
    set(selectedProvider, undefined);
    set(isDetecting, false);
    set(detectionError, undefined);
    providerMap.clear();
    providerChangeListeners.clear();

    logger.info('[UnifiedProviders] Cleanup completed');
  }

  return {
    activeProvider,
    availableProviders: readonly(availableProviders) as Readonly<Ref<EnhancedProviderDetail[]>>,
    checkIfSelectedProvider,
    cleanup,
    clearProvider,
    detectProviders,
    hasSelectedProvider,
    initialize,
    isDetecting: readonly(isDetecting),
    onProviderChanged,
    selectedProvider: readonly(selectedProvider),
    selectedProviderMetadata,
    selectedProviderUuid: readonly(selectedProviderUuid),
    selectProvider,
    showProviderSelection,
  };
}

// Export as shared composable to ensure single instance across app
export const useUnifiedProviders = createSharedComposable(createUnifiedProvidersComposable);
