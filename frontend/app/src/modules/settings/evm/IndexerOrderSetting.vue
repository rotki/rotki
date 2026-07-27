<script setup lang="ts">
import { NotificationGroup, notificationGroupOf, toCapitalCase } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotificationCooldown } from '@/modules/core/notifications/use-notification-cooldown';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import IndexerTabLabel from '@/modules/settings/evm/IndexerTabLabel.vue';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { PrioritizedListData } from '@/modules/settings/types/prioritized-list-data';
import {
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ETHERSCAN_PRIO_LIST_ITEM,
  type PrioritizedListId,
  ROUTESCAN_PRIO_LIST_ITEM,
} from '@/modules/settings/types/prioritized-list-id';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useEvmIndexerSettings } from '@/modules/settings/use-evm-indexer-settings';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';

defineProps<{
  id?: string;
}>();

defineSlots<{
  footer: () => any;
}>();

interface ChainItem {
  id: string;
  name: string;
}

interface TabItem {
  id: string;
  isDefault: boolean;
  name?: string;
}

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const DEFAULT_TAB = 'default';

const { getChain, getChainName, getEvmChainName, txEvmChains } = useSupportedChains();
const { defaultEvmIndexerOrder, evmIndexersOrder } = useEvmIndexerSettings();
const { update: updateSettings } = useSettingsOperations();
const { getApiKey, useApiKey } = useExternalApiKeys();
const { resetSchedule } = useNotificationCooldown();

const { error: defaultWriteError, model: defaultOrderModel, success: defaultWriteSuccess } = useSettingModel('defaultEvmIndexerOrder', { debounce: 0 });
const { error: chainWriteError, model: chainOrdersModel, success: chainWriteSuccess } = useSettingModel('evmIndexersOrder', { debounce: 0 });
const { clearAll: clearDefault, error: defaultError, setError: setDefaultError, setSuccess: setDefaultSuccess, success: defaultSuccess } = useClearableMessages();
const { clearAll: clearChain, error: chainError, setError: setChainError, setSuccess: setChainSuccess, success: chainSuccess } = useClearableMessages();

const pendingChainName = ref<string>('');

const etherscanApiKey = useApiKey('etherscan');

const activeTab = ref<string>(DEFAULT_TAB);
const showChainMenu = ref<boolean>(false);

const localDefaultOrder = ref<PrioritizedListId[]>([]);
const localChainOrders = ref<Record<string, PrioritizedListId[]>>({});

const allIndexerItems = [
  ETHERSCAN_PRIO_LIST_ITEM,
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ROUTESCAN_PRIO_LIST_ITEM,
];

const CHAIN_SUPPORTED_INDEXERS: Record<string, typeof allIndexerItems> = {
  binance_sc: [ETHERSCAN_PRIO_LIST_ITEM],
};

function getAvailableIndexersForChain(chainId: string | null): PrioritizedListData<PrioritizedListId> {
  const items = chainId && chainId in CHAIN_SUPPORTED_INDEXERS
    ? CHAIN_SUPPORTED_INDEXERS[chainId]
    : allIndexerItems;

  return new PrioritizedListData<PrioritizedListId>(items);
}

const availableIndexers = computed<PrioritizedListData<PrioritizedListId>>(() => {
  const tab = get(activeTab);
  const chainId = tab === DEFAULT_TAB ? null : tab;
  return getAvailableIndexersForChain(chainId);
});

const configuredChains = computed<string[]>(() => Object.keys(get(localChainOrders)));

const availableChainItems = computed<ChainItem[]>(() => {
  const configured = get(configuredChains);
  return get(txEvmChains)
    .filter(chain => !configured.includes(chain.id))
    .map(chain => ({
      id: chain.id,
      name: chain.name,
    }));
});

const tabs = computed<TabItem[]>(() => {
  const chainTabs: TabItem[] = get(configuredChains).map(chain => ({
    id: chain,
    isDefault: false,
    name: getChainName(chain),
  }));

  return [
    { id: DEFAULT_TAB, isDefault: true },
    ...chainTabs,
  ];
});

function resetLocalValues(): void {
  const defaultOrder = get(defaultEvmIndexerOrder);
  set(localDefaultOrder, defaultOrder ? [...defaultOrder] : [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT, EvmIndexer.ROUTESCAN]);

  const chainOrders = get(evmIndexersOrder);
  if (chainOrders) {
    // Convert evmChainName keys to chain ids for internal use
    const converted: Record<string, PrioritizedListId[]> = {};
    for (const [evmChainName, order] of Object.entries(chainOrders)) {
      const chain = getChain(evmChainName);
      converted[chain] = [...order];
    }
    set(localChainOrders, converted);
  }
  else {
    set(localChainOrders, {});
  }
}

const evmIndexerValues: string[] = Object.values(EvmIndexer);

function isEvmIndexer(value: PrioritizedListId): value is EvmIndexer {
  return evmIndexerValues.includes(value);
}

function toEvmChainNameKeys(orders: Record<string, PrioritizedListId[]>): Record<string, EvmIndexer[]> {
  const result: Record<string, EvmIndexer[]> = {};
  for (const [chain, order] of Object.entries(orders)) {
    const evmChainName = getEvmChainName(chain);
    if (evmChainName)
      result[evmChainName] = order.filter(isEvmIndexer);
  }
  return result;
}

async function addChain(chain: ChainItem): Promise<void> {
  const orders = { ...get(localChainOrders) };
  const chainAvailableIndexers = getAvailableIndexersForChain(chain.id);
  // Filter default order to only include indexers available for this chain
  const filteredOrder = get(localDefaultOrder).filter(
    indexer => chainAvailableIndexers.itemDataForId(indexer) !== undefined,
  );
  orders[chain.id] = filteredOrder.length > 0 ? filteredOrder : [EvmIndexer.ETHERSCAN];
  set(localChainOrders, orders);
  set(activeTab, chain.id);
  set(showChainMenu, false);
  await updateSettings({ evmIndexersOrder: toEvmChainNameKeys(orders) });
  forgetNoIndexerSchedule();
}

async function removeChain(chain: string): Promise<void> {
  const orders = { ...get(localChainOrders) };
  delete orders[chain];
  set(localChainOrders, orders);
  if (get(activeTab) === chain) {
    set(activeTab, DEFAULT_TAB);
  }
  await updateSettings({ evmIndexersOrder: toEvmChainNameKeys(orders) });
  forgetNoIndexerSchedule();
}

const currentOrder = computed<PrioritizedListId[]>(() => {
  const tab = get(activeTab);
  if (tab === DEFAULT_TAB)
    return get(localDefaultOrder);

  return get(localChainOrders)[tab] ?? [];
});

const chainWarnings = computed<string[]>(() => {
  const tab = get(activeTab);
  if (tab === DEFAULT_TAB)
    return [];

  const warnings: string[] = [];
  const order = get(currentOrder);

  if (tab === 'optimism' && order.includes(EvmIndexer.BLOCKSCOUT))
    warnings.push(t('evm_settings.indexer.chain_warnings.optimism_blockscout'));

  if (tab === 'base' && (order.length === 0 || order[0] !== EvmIndexer.BLOCKSCOUT))
    warnings.push(t('evm_settings.indexer.chain_warnings.base_limited_indexers'));

  return warnings;
});

const missingApiKeyIndexer = computed<string | null>(() => {
  const order = get(currentOrder);
  if (order.length === 0)
    return null;

  const firstIndexer = order[0];

  if (firstIndexer === EvmIndexer.ETHERSCAN) {
    if (!get(etherscanApiKey))
      return toCapitalCase(EvmIndexer.ETHERSCAN);
  }
  else if (firstIndexer === EvmIndexer.BLOCKSCOUT && !getApiKey('blockscout')) {
    return toCapitalCase(EvmIndexer.BLOCKSCOUT);
  }

  return null;
});

function navigateToApiKeys(): void {
  const order = get(currentOrder);
  if (order.length === 0)
    return;

  const firstIndexer = order[0];
  if (firstIndexer === EvmIndexer.ETHERSCAN) {
    router.push({ name: '/api-keys/external/', query: { service: EvmIndexer.ETHERSCAN } });
  }
  else if (firstIndexer === EvmIndexer.BLOCKSCOUT) {
    router.push({ name: '/api-keys/external/', query: { service: EvmIndexer.BLOCKSCOUT } });
  }
}

/**
 * Let the no-indexer warnings interrupt again after the user reorders indexers. Every entry is
 * cleared rather than just the edited chain's, because the default order applies to each chain
 * that has no override of its own.
 */
function forgetNoIndexerSchedule(): void {
  resetSchedule(group => notificationGroupOf(group) === NotificationGroup.NO_AVAILABLE_INDEXERS);
}

function updateDefaultOrder(value: PrioritizedListId[]): void {
  set(localDefaultOrder, value);
  set(defaultOrderModel, value.filter(isEvmIndexer));
  forgetNoIndexerSchedule();
}

function updateChainOrder(chainId: string, value: PrioritizedListId[]): void {
  const orders = { ...get(localChainOrders) };
  orders[chainId] = value;
  set(localChainOrders, orders);
  set(pendingChainName, getChainName(chainId));
  set(chainOrdersModel, toEvmChainNameKeys(orders));
  forgetNoIndexerSchedule();
}

watchImmediate([evmIndexersOrder, defaultEvmIndexerOrder], () => {
  resetLocalValues();
});

watch(defaultOrderModel, () => {
  clearDefault();
});

watch(defaultWriteSuccess, (saved) => {
  if (saved)
    setDefaultSuccess(t('evm_settings.indexer.default_updated'), true);
});

watch(defaultWriteError, (message) => {
  if (message)
    setDefaultError(message, true);
});

watch(chainOrdersModel, () => {
  clearChain();
});

watch(chainWriteSuccess, (saved) => {
  if (saved)
    setChainSuccess(t('evm_settings.indexer.chain_updated', { chain: get(pendingChainName) }), true);
});

watch(chainWriteError, (message) => {
  if (message)
    setChainError(message, true);
});
</script>

<template>
  <div
    :id="id"
    data-cy="indexer-order-setting"
  >
    <div class="pb-5 border-b border-default flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('evm_settings.indexer.title') }}
        </template>
        <template #subtitle>
          {{ t('evm_settings.indexer.subtitle') }}
        </template>
      </SettingCategoryHeader>
    </div>
    <div class="pt-6">
      <div class="flex items-center gap-2 mb-4">
        <RuiTabs
          v-model="activeTab"
          color="primary"
          class="flex-1 !h-auto overflow-hidden"
          data-cy="indexer-tabs"
        >
          <RuiTab
            v-for="tab in tabs"
            :key="tab.id"
            :value="tab.id"
            :data-cy="`indexer-tab-${tab.id}`"
          >
            <IndexerTabLabel
              :tab="tab"
              @remove="removeChain($event)"
            />
          </RuiTab>
        </RuiTabs>

        <RuiMenu
          v-model="showChainMenu"
          :popper="{ placement: 'bottom-end' }"
        >
          <template #activator="{ attrs }">
            <RuiButton
              color="primary"
              variant="outlined"
              v-bind="attrs"
              data-cy="add-chain-button"
              :disabled="availableChainItems.length === 0"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-plus"
                  size="16"
                />
              </template>
              {{ t('evm_settings.indexer.add_chain') }}
            </RuiButton>
          </template>
          <div
            class="max-h-[300px] overflow-y-auto"
            data-cy="chain-menu"
          >
            <RuiButton
              v-for="chain in availableChainItems"
              :key="chain.id"
              variant="list"
              class="w-full"
              :data-cy="`chain-menu-item-${chain.id}`"
              @click="addChain(chain)"
            >
              <template #prepend>
                <ChainIcon
                  :chain="chain.id"
                  size="20px"
                />
              </template>
              {{ chain.name }}
            </RuiButton>
          </div>
        </RuiMenu>
      </div>

      <RuiDivider class="mb-4" />

      <RuiAlert
        v-if="currentOrder.length === 0"
        type="warning"
        class="mb-4"
      >
        {{ t('evm_settings.indexer.no_indexers_warning') }}
      </RuiAlert>

      <RuiAlert
        v-else-if="missingApiKeyIndexer"
        type="info"
        class="mb-4"
        data-cy="missing-api-key-alert"
      >
        <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
          <span class="flex-1">
            {{ t('evm_settings.indexer.api_key_missing_alert', { indexer: missingApiKeyIndexer }) }}
          </span>
          <RuiButton
            color="info"
            size="sm"
            @click="navigateToApiKeys()"
          >
            {{ t('evm_settings.indexer.enter_api_key') }}
          </RuiButton>
        </div>
      </RuiAlert>

      <RuiAlert
        v-for="(warning, index) in chainWarnings"
        :key="index"
        type="warning"
        class="mb-4"
        data-cy="chain-warning-alert"
      >
        {{ warning }}
      </RuiAlert>

      <RuiTabItems v-model="activeTab">
        <RuiTabItem
          v-for="tab in tabs"
          :key="tab.id"
          :value="tab.id"
        >
          <PrioritizedList
            v-if="tab.isDefault"
            data-cy="default-indexer-order"
            :model-value="localDefaultOrder"
            :all-items="availableIndexers"
            :status="{ error: defaultError, success: defaultSuccess }"
            :item-data-name="t('evm_settings.indexer.data_name')"
            :disable-delete="localDefaultOrder.length <= 1"
            @update:model-value="updateDefaultOrder($event)"
          >
            <template #title>
              {{ t('evm_settings.indexer.default_order') }}
            </template>
          </PrioritizedList>
          <PrioritizedList
            v-else
            :data-cy="`chain-indexer-order-${tab.id}`"
            :model-value="localChainOrders[tab.id] ?? []"
            :all-items="availableIndexers"
            :status="{ error: chainError, success: chainSuccess }"
            :item-data-name="t('evm_settings.indexer.data_name')"
            :disable-delete="(localChainOrders[tab.id]?.length ?? 0) <= 1"
            @update:model-value="updateChainOrder(tab.id, $event)"
          >
            <template #title>
              {{ t('evm_settings.indexer.chain_order', { chain: tab.name }) }}
            </template>
          </PrioritizedList>
        </RuiTabItem>
      </RuiTabItems>
      <slot name="footer" />
    </div>
  </div>
</template>
