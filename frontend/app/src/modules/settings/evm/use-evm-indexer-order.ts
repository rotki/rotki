import type { ComputedRef, Ref } from 'vue';
import type { MessageKey } from '@/message-key';
import type { PrioritizedListData } from '@/modules/settings/types/prioritized-list-data';
import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import { NotificationGroup, notificationGroupOf } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotificationCooldown } from '@/modules/core/notifications/use-notification-cooldown';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { buildTabs, type ChainItem, DEFAULT_INDEXER_ORDER, DEFAULT_INDEXER_TAB, getAvailableChainItems, getAvailableIndexersForChain, getChainIndexerWarnings, getMissingApiKeyIndexer, isEvmIndexer, keyedPrimaryIndexer, orderForChain, type TabItem, toChainIdKeys, toEvmChainNameKeys } from '@/modules/settings/evm/evm-indexer-utils';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { useEvmIndexerSettings } from '@/modules/settings/use-evm-indexer-settings';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import { useSettingWriteFeedback } from '@/modules/settings/use-setting-write-feedback';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseEvmIndexerOrderReturn {
  readonly modelActiveTab: Ref<string>;
  readonly tabs: ComputedRef<TabItem[]>;
  readonly availableChainItems: ComputedRef<ChainItem[]>;
  readonly availableIndexers: ComputedRef<PrioritizedListData<PrioritizedListId>>;
  readonly currentOrder: ComputedRef<PrioritizedListId[]>;
  readonly defaultOrder: ComputedRef<PrioritizedListId[]>;
  readonly chainOrders: ComputedRef<Record<string, PrioritizedListId[]>>;
  readonly chainWarnings: ComputedRef<MessageKey[]>;
  readonly missingApiKeyIndexer: ComputedRef<string | undefined>;
  readonly defaultError: Readonly<Ref<string>>;
  readonly defaultSuccess: Readonly<Ref<string>>;
  readonly chainError: Readonly<Ref<string>>;
  readonly chainSuccess: Readonly<Ref<string>>;
  readonly addChain: (chain: ChainItem) => Promise<void>;
  readonly removeChain: (chain: string) => Promise<void>;
  readonly updateDefaultOrder: (value: PrioritizedListId[]) => void;
  readonly updateChainOrder: (chainId: string, value: PrioritizedListId[]) => void;
  readonly primaryIndexerService: () => EvmIndexer | undefined;
}

/**
 * Local editing state for the EVM indexer order: the global default plus the per-chain overrides,
 * the tab they are edited under, and the write feedback for each of the two settings.
 *
 * The local orders are keyed by chain id while the settings are keyed by evm chain name, so every
 * read converts inwards and every write converts back out.
 */
export function useEvmIndexerOrder(): UseEvmIndexerOrderReturn {
  const { t } = useI18n({ useScope: 'global' });

  const modelActiveTab = shallowRef<string>(DEFAULT_INDEXER_TAB);
  const pendingChainName = shallowRef<string>('');
  const localDefaultOrder = ref<PrioritizedListId[]>([]);
  const localChainOrders = ref<Record<string, PrioritizedListId[]>>({});

  const { getChain, getChainName, getEvmChainName, txEvmChains } = useSupportedChains();
  const { defaultEvmIndexerOrder, evmIndexersOrder } = useEvmIndexerSettings();
  const { update: updateSettings } = useSettingsOperations();
  const { useApiKey } = useExternalApiKeys();
  const { resetSchedule } = useNotificationCooldown();

  const defaultOrderState = useSettingModel('defaultEvmIndexerOrder', { debounce: 0 });
  const chainOrdersState = useSettingModel('evmIndexersOrder', { debounce: 0 });

  const { error: defaultError, success: defaultSuccess } = useSettingWriteFeedback(
    defaultOrderState,
    () => t('evm_settings.indexer.default_updated'),
  );
  const { error: chainError, success: chainSuccess } = useSettingWriteFeedback(
    chainOrdersState,
    () => t('evm_settings.indexer.chain_updated', { chain: get(pendingChainName) }),
  );

  const etherscanApiKey = useApiKey('etherscan');
  const blockscoutApiKey = useApiKey('blockscout');

  const configuredChains = computed<string[]>(() => Object.keys(get(localChainOrders)));

  const availableIndexers = computed<PrioritizedListData<PrioritizedListId>>(() => {
    const tab = get(modelActiveTab);
    return getAvailableIndexersForChain(tab === DEFAULT_INDEXER_TAB ? null : tab);
  });

  const availableChainItems = computed<ChainItem[]>(() =>
    getAvailableChainItems(get(txEvmChains), get(configuredChains)),
  );

  const tabs = computed<TabItem[]>(() => buildTabs(get(configuredChains), getChainName));

  const currentOrder = computed<PrioritizedListId[]>(() => {
    const tab = get(modelActiveTab);
    if (tab === DEFAULT_INDEXER_TAB)
      return get(localDefaultOrder);

    return get(localChainOrders)[tab] ?? [];
  });

  const defaultOrder = computed<PrioritizedListId[]>(() => get(localDefaultOrder));

  const chainOrders = computed<Record<string, PrioritizedListId[]>>(() => get(localChainOrders));

  const chainWarnings = computed<MessageKey[]>(() => getChainIndexerWarnings(get(modelActiveTab), get(currentOrder)));

  const missingApiKeyIndexer = computed<string | undefined>(() => getMissingApiKeyIndexer(
    get(currentOrder),
    indexer => !!(indexer === EvmIndexer.ETHERSCAN ? get(etherscanApiKey) : get(blockscoutApiKey)),
  ));

  /**
   * Let the no-indexer warnings interrupt again after the user reorders indexers. Every entry is
   * cleared rather than just the edited chain's, because the default order applies to each chain
   * that has no override of its own.
   */
  function forgetNoIndexerSchedule(): void {
    resetSchedule(group => notificationGroupOf(group) === NotificationGroup.NO_AVAILABLE_INDEXERS);
  }

  async function persistChainOrders(orders: Record<string, PrioritizedListId[]>): Promise<void> {
    await updateSettings({ evmIndexersOrder: toEvmChainNameKeys(orders, getEvmChainName) });
    forgetNoIndexerSchedule();
  }

  async function addChain(chain: ChainItem): Promise<void> {
    const orders = { ...get(localChainOrders), [chain.id]: orderForChain(chain.id, get(localDefaultOrder)) };
    set(localChainOrders, orders);
    set(modelActiveTab, chain.id);
    await persistChainOrders(orders);
  }

  async function removeChain(chain: string): Promise<void> {
    const orders = { ...get(localChainOrders) };
    delete orders[chain];
    set(localChainOrders, orders);
    if (get(modelActiveTab) === chain)
      set(modelActiveTab, DEFAULT_INDEXER_TAB);

    await persistChainOrders(orders);
  }

  function updateDefaultOrder(value: PrioritizedListId[]): void {
    set(localDefaultOrder, value);
    set(defaultOrderState.model, value.filter(isEvmIndexer));
    forgetNoIndexerSchedule();
  }

  function updateChainOrder(chainId: string, value: PrioritizedListId[]): void {
    const orders = { ...get(localChainOrders), [chainId]: value };
    set(localChainOrders, orders);
    set(pendingChainName, getChainName(chainId));
    set(chainOrdersState.model, toEvmChainNameKeys(orders, getEvmChainName));
    forgetNoIndexerSchedule();
  }

  /** The keyed indexer the api-key prompt refers to, for routing to its settings row. */
  function primaryIndexerService(): EvmIndexer | undefined {
    return keyedPrimaryIndexer(get(currentOrder));
  }

  function resetLocalValues(): void {
    const defaultOrder = get(defaultEvmIndexerOrder);
    set(localDefaultOrder, defaultOrder ? [...defaultOrder] : [...DEFAULT_INDEXER_ORDER]);
    set(localChainOrders, toChainIdKeys(get(evmIndexersOrder), getChain));
  }

  watchImmediate([evmIndexersOrder, defaultEvmIndexerOrder], () => {
    resetLocalValues();
  });

  return {
    addChain,
    availableChainItems,
    availableIndexers,
    chainError,
    chainOrders,
    chainSuccess,
    chainWarnings,
    currentOrder,
    defaultError,
    defaultOrder,
    defaultSuccess,
    missingApiKeyIndexer,
    modelActiveTab,
    primaryIndexerService,
    removeChain,
    tabs,
    updateChainOrder,
    updateDefaultOrder,
  };
}
