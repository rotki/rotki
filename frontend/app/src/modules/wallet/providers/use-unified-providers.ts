import type { EIP1193Provider, EIP6963ProviderInfo } from '@/types';
import { wait } from '@shared/utils';
import { createSharedComposable, get, set, useLocalStorage } from '@vueuse/core';
import { computed, type ComputedRef, readonly, ref, type Ref } from 'vue';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { type EnhancedProviderDetail, getAllWalletProviders, type ProviderDetectionOptions } from './provider-detection';

interface ProviderPreferences {
  lastSelectedUuid?: string;
  autoSelectSingle: boolean;
}

interface ClearProviderOptions {
  /**
   * Whether to also forget the persisted `lastSelectedUuid`. Defaults to `true`, which is
   * what a deliberate disconnect wants; session teardown passes `false` so the remembered
   * provider survives to the next login.
   */
  forget?: boolean;
}

interface UnifiedDetectionOptions extends ProviderDetectionOptions {
  maxRetries?: number;
  retryDelay?: number;
}

const DETECTION_DEFAULTS: Required<UnifiedDetectionOptions> = {
  includeLegacy: true,
  maxRetries: 3,
  retryDelay: 500,
  timeout: 2000,
};

type OnProviderChangedCallback = (provider: EIP1193Provider | undefined, oldProvider: EIP1193Provider | undefined) => void;

interface UnifiedProvidersComposable {
  availableProviders: Readonly<Ref<EnhancedProviderDetail[]>>;
  selectedProvider: Readonly<Ref<EnhancedProviderDetail | undefined>>;
  selectedProviderUuid: Readonly<Ref<string | undefined>>;
  activeProvider: ComputedRef<EIP1193Provider | undefined>;
  selectedProviderMetadata: ComputedRef<EIP6963ProviderInfo | undefined>;
  isDetecting: Readonly<Ref<boolean>>;
  hasSelectedProvider: ComputedRef<boolean>;
  showProviderSelection: Ref<boolean>;
  detectProviders: (options?: UnifiedDetectionOptions) => Promise<EnhancedProviderDetail[]>;
  selectProvider: (uuid: string) => Promise<boolean>;
  clearProvider: (options?: ClearProviderOptions) => void;
  checkIfSelectedProvider: () => Promise<boolean>;
  onProviderChanged: (callback: OnProviderChangedCallback) => () => void;
  initialize: () => void;
  cleanup: () => void;
}

function createUnifiedProvidersComposable(): UnifiedProvidersComposable {
  const availableProviders = ref<EnhancedProviderDetail[]>([]);
  const selectedProvider = ref<EnhancedProviderDetail>();
  const isDetecting = ref<boolean>(false);
  const detectionError = ref<string>();
  const showProviderSelection = ref<boolean>(false);

  /** Persisted, so a returning user does not have to pick their wallet again. */
  const preferences = useLocalStorage<ProviderPreferences>('rotki-provider-preferences', {
    autoSelectSingle: true,
  });

  const providerChangeListeners = new Set<OnProviderChangedCallback>();
  const providerMap = new Map<string, EIP1193Provider>();
  const isElectronMode = computed<boolean>(() => !!window.walletBridge);

  const selectedProviderUuid = computed<string | undefined>(() => get(selectedProvider)?.info.uuid);
  const activeProvider = computed<EIP1193Provider | undefined>(() => get(selectedProvider)?.provider);
  const selectedProviderMetadata = computed<EIP6963ProviderInfo | undefined>(() => get(selectedProvider)?.info);
  const hasSelectedProvider = computed<boolean>(() => !!get(selectedProvider));

  /** Under Electron the bridge owns the selection, so the local ref is not the answer. */
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

  /**
   * Polls for providers until some appear or the retries run out. A round that finds nothing is not an
   * error, so it waits and tries again; a throwing round is only propagated on the final attempt.
   */
  async function detectWithRetry(
    settings: Required<UnifiedDetectionOptions>,
  ): Promise<EnhancedProviderDetail[]> {
    const { includeLegacy, maxRetries, retryDelay, timeout } = settings;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      logger.debug(`[UnifiedProviders] Detection attempt ${attempt + 1}/${maxRetries + 1}`);

      try {
        const detected = await getAllWalletProviders({ includeLegacy, timeout });
        if (detected.length > 0)
          return detected;
      }
      catch (error) {
        logger.warn(`[UnifiedProviders] Detection attempt ${attempt + 1} failed:`, error);

        if (attempt === maxRetries)
          throw error;
      }

      if (attempt < maxRetries)
        await wait(retryDelay);
    }

    return [];
  }

  function indexProviders(detected: EnhancedProviderDetail[]): void {
    providerMap.clear();
    for (const provider of detected)
      providerMap.set(provider.info.uuid, provider.provider);
  }

  function countBySource(detected: EnhancedProviderDetail[]): Record<string, number> {
    const breakdown: Record<string, number> = {};
    for (const { source } of detected)
      breakdown[source] = (breakdown[source] ?? 0) + 1;

    return breakdown;
  }

  /** Detection with retries, since an extension can announce itself after the page has loaded. */
  async function detectProviders(options: UnifiedDetectionOptions = {}): Promise<EnhancedProviderDetail[]> {
    // Spread rather than per-field defaults: the rule counts each defaulted field as a branch.
    const settings = { ...DETECTION_DEFAULTS, ...options };

    set(isDetecting, true);
    set(detectionError, undefined);

    try {
      logger.debug('[UnifiedProviders] Starting provider detection with options:', options);
      logger.debug(`[UnifiedProviders] Environment: ${get(isElectronMode) ? 'Electron' : 'Browser'} mode`);

      const detectedProviders = await detectWithRetry(settings);

      indexProviders(detectedProviders);
      set(availableProviders, detectedProviders);

      logger.info(
        `[UnifiedProviders] Detected ${detectedProviders.length} providers:`,
        countBySource(detectedProviders),
      );

      await handleAutoSelection();

      return detectedProviders;
    }
    catch (error: unknown) {
      logger.error('[UnifiedProviders] Provider detection failed:', error);
      set(detectionError, getErrorMessage(error) || 'Failed to detect providers');
      set(availableProviders, []);
      return [];
    }
    finally {
      set(isDetecting, false);
    }
  }

  /**
   * Picks a provider without asking, in order: the only one there is, then the one used last if it
   * is still around, then {@link handleSmartAutoSelection}.
   */
  async function handleAutoSelection(): Promise<void> {
    const currentProviders = get(availableProviders);
    const prefs = get<ProviderPreferences>(preferences);

    if (!prefs.autoSelectSingle || currentProviders.length === 0) {
      return;
    }

    if (currentProviders.length === 1) {
      await selectProvider(currentProviders[0].info.uuid);
      return;
    }

    if (prefs.lastSelectedUuid) {
      const previousProvider = currentProviders.find(p => p.info.uuid === prefs.lastSelectedUuid);
      if (previousProvider) {
        logger.debug(`[UnifiedProviders] Restoring previously selected provider: ${previousProvider.info.name}`);
        await selectProvider(previousProvider.info.uuid);
        return;
      }
    }

    await handleSmartAutoSelection(currentProviders);
  }

  /**
   * Bridge providers first under Electron, then eip6963, then legacy. Only ever picks when a tier
   * holds exactly one candidate; anything ambiguous opens the picker instead.
   */
  async function handleSmartAutoSelection(providers: EnhancedProviderDetail[]): Promise<void> {
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

  /** An empty uuid clears the selection, so a picker can bind one function to both. */
  async function selectProvider(uuid: string): Promise<boolean> {
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

    set(preferences, {
      ...get<ProviderPreferences>(preferences),
      lastSelectedUuid: uuid,
    });

    notifyProviderChanged(provider.provider, oldProvider);

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

  /**
   * Only a deliberate disconnect forgets the remembered choice. Session teardown (logout, user
   * switch) clears the active selection and keeps it, or the next login has to pick again.
   */
  function clearProvider({ forget = true }: ClearProviderOptions = {}): void {
    const previousProvider = get(selectedProvider);

    set(selectedProvider, undefined);

    if (forget) {
      set(preferences, {
        ...get<ProviderPreferences>(preferences),
        lastSelectedUuid: undefined,
      });
    }

    notifyProviderChanged(undefined, previousProvider?.provider);

    if (previousProvider) {
      logger.info(`[UnifiedProviders] Cleared provider selection: ${previousProvider.info.name}`);
    }
  }

  /** @returns a function that removes the listener again. */
  const onProviderChanged = (callback: OnProviderChangedCallback): (() => void) => {
    providerChangeListeners.add(callback);
    return () => {
      providerChangeListeners.delete(callback);
    };
  };

  function initialize(): void {
    logger.info(`[UnifiedProviders] Initializing in ${get(isElectronMode) ? 'Electron' : 'Browser'} mode`);

    detectProviders().catch((error) => {
      logger.error('[UnifiedProviders] Initial provider detection failed:', error);
    });
  }

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
    availableProviders: computed<EnhancedProviderDetail[]>(() => get(availableProviders)),
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

/** Shared, so every caller sees the same selection and the same listener set. */
export const useUnifiedProviders = createSharedComposable(createUnifiedProvidersComposable);
