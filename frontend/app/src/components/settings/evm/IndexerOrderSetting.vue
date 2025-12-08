<script setup lang="ts">
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { EvmIndexer } from '@/types/settings/evm-indexer';
import { PrioritizedListData } from '@/types/settings/prioritized-list-data';
import {
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ETHERSCAN_PRIO_LIST_ITEM,
  type PrioritizedListId,
  ROUTESCAN_PRIO_LIST_ITEM,
} from '@/types/settings/prioritized-list-id';

defineProps<{
  id?: string;
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

const DEFAULT_TAB = 'default';

const { getChain, getChainName, getEvmChainName, txEvmChains } = useSupportedChains();
const { defaultEvmIndexerOrder, evmIndexersOrder } = storeToRefs(useGeneralSettingsStore());
const { update: updateSettings } = useSettingsStore();

const activeTab = ref<string>(DEFAULT_TAB);
const showChainMenu = ref<boolean>(false);

const localDefaultOrder = ref<PrioritizedListId[]>([]);
const localChainOrders = ref<Record<string, PrioritizedListId[]>>({});

const availableIndexers = new PrioritizedListData<PrioritizedListId>([
  ETHERSCAN_PRIO_LIST_ITEM,
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ROUTESCAN_PRIO_LIST_ITEM,
]);

const configuredChains = computed<string[]>(() => Object.keys(get(localChainOrders)));

const availableChainItems = computed<ChainItem[]>(() => {
  const configured = get(configuredChains);
  return get(txEvmChains)
    .filter(chain => !configured.includes(chain.id))
    .map(chain => ({
      id: chain.id,
      name: get(getChainName(chain.id)),
    }));
});

const tabs = computed<TabItem[]>(() => {
  const chainTabs: TabItem[] = get(configuredChains).map(chain => ({
    id: chain,
    isDefault: false,
    name: get(getChainName(chain)),
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
  orders[chain.id] = [...get(localDefaultOrder)];
  set(localChainOrders, orders);
  set(activeTab, chain.id);
  set(showChainMenu, false);
  await updateSettings({ evmIndexersOrder: toEvmChainNameKeys(orders) });
}

async function removeChain(chain: string): Promise<void> {
  const orders = { ...get(localChainOrders) };
  delete orders[chain];
  set(localChainOrders, orders);
  if (get(activeTab) === chain) {
    set(activeTab, DEFAULT_TAB);
  }
  await updateSettings({ evmIndexersOrder: toEvmChainNameKeys(orders) });
}

const currentOrder = computed<PrioritizedListId[]>(() => {
  const tab = get(activeTab);
  if (tab === DEFAULT_TAB)
    return get(localDefaultOrder);

  return get(localChainOrders)[tab] ?? [];
});

function updateDefaultOrder(value: PrioritizedListId[], updateImmediate: (value: PrioritizedListId[]) => void): void {
  set(localDefaultOrder, value);
  updateImmediate(value);
}

function updateChainOrder(chainId: string, value: PrioritizedListId[], updateImmediate: (value: PrioritizedListId[]) => void): void {
  const orders = { ...get(localChainOrders) };
  orders[chainId] = value;
  set(localChainOrders, orders);
  updateImmediate(value);
}

watchImmediate([evmIndexersOrder, defaultEvmIndexerOrder], () => {
  resetLocalValues();
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
            <div class="flex items-center gap-2">
              <template v-if="tab.isDefault">
                <RuiIcon
                  name="lu-globe"
                  size="16"
                />
                <span>{{ t('evm_settings.indexer.default_tab') }}</span>
              </template>
              <template v-else>
                <ChainIcon
                  :chain="tab.id"
                  size="16px"
                />
                <span>{{ tab.name }}</span>
                <RuiTooltip
                  :popper="{ placement: 'top' }"
                  :open-delay="400"
                >
                  <template #activator>
                    <RuiButton
                      variant="text"
                      icon
                      size="sm"
                      class="!p-0.5"
                      :data-cy="`remove-chain-${tab.id}`"
                      @click.stop="removeChain(tab.id)"
                    >
                      <RuiIcon
                        name="lu-x"
                        size="14"
                      />
                    </RuiButton>
                  </template>
                  {{ t('evm_settings.indexer.remove_chain') }}
                </RuiTooltip>
              </template>
            </div>
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

      <RuiTabItems v-model="activeTab">
        <RuiTabItem
          v-for="tab in tabs"
          :key="tab.id"
          :value="tab.id"
        >
          <SettingsOption
            v-if="tab.isDefault"
            #default="{ error, success, updateImmediate }"
            setting="defaultEvmIndexerOrder"
            :success-message="t('evm_settings.indexer.default_updated')"
            @finished="resetLocalValues()"
          >
            <PrioritizedList
              data-cy="default-indexer-order"
              :model-value="localDefaultOrder"
              :all-items="availableIndexers"
              :status="{ error, success }"
              :item-data-name="t('evm_settings.indexer.data_name')"
              :disable-delete="localDefaultOrder.length <= 1"
              @update:model-value="updateDefaultOrder($event, updateImmediate)"
            >
              <template #title>
                {{ t('evm_settings.indexer.default_order') }}
              </template>
            </PrioritizedList>
          </SettingsOption>
          <SettingsOption
            v-else
            #default="{ error, success, updateImmediate }"
            setting="evmIndexersOrder"
            :transform="() => toEvmChainNameKeys(localChainOrders)"
            :success-message="t('evm_settings.indexer.chain_updated', { chain: tab.name })"
            @finished="resetLocalValues()"
          >
            <PrioritizedList
              :data-cy="`chain-indexer-order-${tab.id}`"
              :model-value="localChainOrders[tab.id] ?? []"
              :all-items="availableIndexers"
              :status="{ error, success }"
              :item-data-name="t('evm_settings.indexer.data_name')"
              :disable-delete="(localChainOrders[tab.id]?.length ?? 0) <= 1"
              @update:model-value="updateChainOrder(tab.id, $event, updateImmediate)"
            >
              <template #title>
                {{ t('evm_settings.indexer.chain_order', { chain: tab.name }) }}
              </template>
            </PrioritizedList>
          </SettingsOption>
        </RuiTabItem>
      </RuiTabItems>
    </div>
  </div>
</template>
