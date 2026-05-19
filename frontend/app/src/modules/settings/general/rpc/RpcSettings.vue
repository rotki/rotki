<script setup lang="ts">
import type { Component } from 'vue';
import type BlockchainRpcNodeManager from '@/modules/settings/general/rpc/BlockchainRpcNodeManager.vue';
import type SimpleRpcNodeManager from '@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue';
import { assert, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getPublicProtocolImagePath, getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { isOfEnum } from '@/modules/core/common/helpers/is-of-enum';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import RpcSettingOption from '@/modules/settings/general/rpc/RpcSettingOption.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';

const { t } = useI18n({ useScope: 'global' });

const route = useRoute();
const router = useRouter();

interface ChainRpcSettingTab {
  chain: Blockchain;
  component: Component;
  setting?: string;
}

interface CustomRpcSettingTab {
  id: string;
  name: string;
  image: string;
  component: Component;
  setting?: string;
}

type RpcSettingTab = ChainRpcSettingTab | CustomRpcSettingTab;

// Key-based selection (chain id or custom tab id) — survives the tab list
// being populated asynchronously (txEvmChains may load after mount).
const selectedKey = ref<string>(Blockchain.ETH);
const evmRpcNodeManagerRef = useTemplateRef<InstanceType<typeof BlockchainRpcNodeManager | typeof SimpleRpcNodeManager>[]>('evmRpcNodeManagerRef');
const railRef = useTemplateRef<HTMLDivElement>('railRef');

const { getChainName, txEvmChains } = useSupportedChains();
const { isMdAndUp } = useBreakpoint();

const evmChainTabs = useArrayMap(txEvmChains, (chain) => {
  assert(isOfEnum(Blockchain)(chain.id));
  return {
    chain: chain.id,
    component: defineAsyncComponent(() => import('@/modules/settings/general/rpc/BlockchainRpcNodeManager.vue')),
  } satisfies RpcSettingTab;
});

const otherTabs = computed<RpcSettingTab[]>(() => [
  {
    // Solana is non-EVM but uses the same multi-node RPC manager as EVM chains.
    chain: Blockchain.SOLANA,
    component: defineAsyncComponent(() => import('@/modules/settings/general/rpc/BlockchainRpcNodeManager.vue')),
  },
  {
    component: defineAsyncComponent(() => import('@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue')),
    id: 'btc_mempool_space',
    image: getPublicServiceImagePath('mempool.png'),
    name: 'Bitcoin Mempool',
    setting: 'btcMempoolApi',
  },
  {
    chain: Blockchain.KSM,
    component: defineAsyncComponent(() => import('@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue')),
    setting: 'ksmRpcEndpoint',
  },
  {
    chain: Blockchain.DOT,
    component: defineAsyncComponent(() => import('@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue')),
    setting: 'dotRpcEndpoint',
  },
  {
    component: defineAsyncComponent(() => import('@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue')),
    id: 'eth_consensus_layer',
    image: getPublicProtocolImagePath('ethereum.svg'),
    name: 'ETH Beacon Node',
    setting: 'beaconRpcEndpoint',
  },
]);

const rpcSettingTabs = computed<RpcSettingTab[]>(() => [
  ...get(evmChainTabs),
  ...get(otherTabs),
]);

interface RailOption {
  key: string;
  label: string;
  tab: RpcSettingTab;
  group: 'evm' | 'other';
}

function tabKey(tab: RpcSettingTab): string {
  return isChain(tab) ? tab.chain : tab.id;
}

function toRailOption(group: 'evm' | 'other') {
  return (tab: RpcSettingTab): RailOption => ({
    key: tabKey(tab),
    label: isChain(tab) ? getChainName(tab.chain) : tab.name,
    tab,
    group,
  });
}

const evmRailOptions = computed<RailOption[]>(() => get(evmChainTabs).map(toRailOption('evm')));

const otherRailOptions = computed<RailOption[]>(() => get(otherTabs).map(toRailOption('other')));

const allRailOptions = computed<RailOption[]>(() => [...get(evmRailOptions), ...get(otherRailOptions)]);

const firstOtherKey = computed<string | undefined>(() => get(otherRailOptions)[0]?.key);

const activeTab = computed<RpcSettingTab | undefined>(() => {
  const key = get(selectedKey);
  return get(rpcSettingTabs).find(tab => tabKey(tab) === key);
});

// Single-value endpoints (BTC Mempool, KSM, DOT, Beacon) carry a `setting` key
// and only ever store one URL — the "Add node" button doesn't apply.
const canAddNode = computed<boolean>(() => {
  const tab = get(activeTab);
  return !!tab && !tab.setting;
});

function isChain(item: RpcSettingTab): item is ChainRpcSettingTab {
  return 'chain' in item;
}

function selectTab(key: string | null | undefined): void {
  if (key)
    set(selectedKey, key);
}

function addNodeClick(): void {
  const refElement = get(evmRpcNodeManagerRef);
  if (refElement?.[0]) {
    refElement[0].addNewRpcNode();
  }
}

function scrollActiveIntoView(): void {
  startPromise(nextTick(() => {
    const active = get(railRef)?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]');
    active?.scrollIntoView({ block: 'nearest' });
  }));
}

onMounted(() => {
  const tabQuery = get(route).query.tab;
  if (typeof tabQuery === 'string' && tabQuery)
    set(selectedKey, tabQuery);
  scrollActiveIntoView();
});

watch(selectedKey, (key) => {
  if (!key)
    return;
  const currentRoute = get(route);
  if (currentRoute.query.tab !== key) {
    startPromise(router.replace({
      query: { ...currentRoute.query, tab: key },
    }));
  }
  scrollActiveIntoView();
});

// When the chain list populates after mount, re-scroll so the active rail item
// is visible (relevant for deep-links into entries far down the list).
watch(rpcSettingTabs, () => scrollActiveIntoView());
</script>

<template>
  <div
    :id="SettingsHighlightIds.RPC_NODES"
    class="mt-4 md:h-full md:flex md:flex-col md:min-h-0"
  >
    <div class="pb-5 border-b border-default flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('general_settings.rpc_node_setting.title') }}
        </template>
        <template #subtitle>
          {{ t('general_settings.rpc_node_setting.subtitle') }}
        </template>
      </SettingCategoryHeader>
      <RuiButton
        v-if="canAddNode"
        color="primary"
        data-cy="add-node"
        data-testid="add-node"
        @click="addNodeClick()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="16"
          />
        </template>
        {{ t('evm_rpc_node_manager.add_button') }}
      </RuiButton>
    </div>
    <div class="pt-6 md:flex md:items-stretch md:gap-6 md:flex-1 md:min-h-0">
      <template v-if="isMdAndUp">
        <div
          ref="railRef"
          class="w-[220px] shrink-0 flex flex-col gap-4 md:overflow-y-auto md:pr-1 md:-mr-1"
          data-testid="rpc-settings-rail"
        >
          <div>
            <div class="px-3 pb-2 text-xs font-medium uppercase tracking-wider text-rui-text-secondary">
              {{ t('general_settings.rpc_node_setting.groups.evm') }}
            </div>
            <RuiTabs
              vertical
              indicator-position="start"
              color="primary"
              class="!h-auto"
            >
              <RuiTab
                v-for="option in evmRailOptions"
                :key="option.key"
                align="start"
                :active="selectedKey === option.key"
                @click="selectTab(option.key)"
              >
                <RpcSettingOption :tab="option.tab" />
              </RuiTab>
            </RuiTabs>
          </div>
          <div>
            <div class="px-3 pb-2 text-xs font-medium uppercase tracking-wider text-rui-text-secondary">
              {{ t('general_settings.rpc_node_setting.groups.other') }}
            </div>
            <RuiTabs
              vertical
              indicator-position="start"
              color="primary"
              class="!h-auto"
            >
              <RuiTab
                v-for="option in otherRailOptions"
                :key="option.key"
                align="start"
                :active="selectedKey === option.key"
                @click="selectTab(option.key)"
              >
                <RpcSettingOption :tab="option.tab" />
              </RuiTab>
            </RuiTabs>
          </div>
        </div>
      </template>
      <template v-else>
        <div
          class="pb-4 w-full"
          data-testid="rpc-settings-dropdowns"
        >
          <RuiMenuSelect
            :model-value="selectedKey"
            :options="allRailOptions"
            :label="t('general_settings.rpc_node_setting.title')"
            variant="outlined"
            key-attr="key"
            text-attr="label"
            :hide-details="true"
            @update:model-value="selectTab($event)"
          >
            <template #item="{ item }">
              <RpcSettingOption
                :tab="item.tab"
                :group-label="item.key === firstOtherKey ? t('general_settings.rpc_node_setting.groups.other') : undefined"
              />
            </template>
            <template #selection="{ item }">
              <RpcSettingOption :tab="item.tab" />
            </template>
          </RuiMenuSelect>
        </div>
      </template>

      <div class="flex-1 min-w-0 md:overflow-y-auto">
        <RuiDivider
          v-if="!isMdAndUp"
          class="mb-4"
        />
        <template v-for="tab in rpcSettingTabs">
          <div
            v-if="tabKey(tab) === selectedKey"
            :key="tabKey(tab)"
          >
            <Component
              :is="tab.component"
              v-if="!tab.setting && 'chain' in tab"
              ref="evmRpcNodeManagerRef"
              :chain="tab.chain"
            />
            <Component
              :is="tab.component"
              v-else
              ref="evmRpcNodeManagerRef"
              :setting="tab.setting"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
