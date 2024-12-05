<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { isOfEnum } from '@/utils';
import type { Component } from 'vue';
import type EvmRpcNodeManager from '@/components/settings/general/rpc/EvmRpcNodeManager.vue';

const { t } = useI18n();

interface ChainRpcSettingTab {
  chain: Blockchain;
  component: Component;
}

interface CustomRpcSettingTab {
  id: string;
  name: string;
  image: string;
  component: Component;
}

type RpcSettingTab = ChainRpcSettingTab | CustomRpcSettingTab;

const rpcSettingTab = ref<number>(0);
const evmRpcNodeManagerRef = ref<InstanceType<typeof EvmRpcNodeManager>[]>();

const { txEvmChains } = useSupportedChains();
const evmChainTabs = useArrayMap(txEvmChains, (chain) => {
  assert(isOfEnum(Blockchain)(chain.id));
  return {
    chain: chain.id,
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/EvmRpcNodeManager.vue')),
  } satisfies RpcSettingTab;
});

const rpcSettingTabs = computed<RpcSettingTab[]>(() => [
  ...get(evmChainTabs),
  {
    chain: Blockchain.KSM,
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/KsmRpcSetting.vue')),
  },
  {
    chain: Blockchain.DOT,
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/DotRpcSetting.vue')),
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/BeaconchainRpcSetting.vue')),
    id: 'eth_consensus_layer',
    image: './assets/images/protocols/ethereum.svg',
    name: 'ETH Beacon Node',
  },
]);

function isChain(item: RpcSettingTab): item is ChainRpcSettingTab {
  return 'chain' in item;
}

function isTxEvmChain(index: number) {
  return index < get(evmChainTabs).length;
}

function addNodeClick() {
  const refElement = get(evmRpcNodeManagerRef);
  if (refElement?.[0]) {
    refElement[0].addNewRpcNode();
  }
}
</script>

<template>
  <div>
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
        v-if="isTxEvmChain(rpcSettingTab)"
        color="primary"
        data-cy="add-node"
        @click="addNodeClick()"
      >
        {{ t('evm_rpc_node_manager.add_button') }}
      </RuiButton>
    </div>
    <div class="pt-6">
      <RuiTabs
        v-model="rpcSettingTab"
        color="primary"
        class="!h-auto"
      >
        <RuiTab
          v-for="tab in rpcSettingTabs"
          :key="isChain(tab) ? tab.chain : tab.id"
        >
          <LocationDisplay
            v-if="isChain(tab)"
            :open-details="false"
            :identifier="tab.chain"
            horizontal
            size="16px"
          />

          <div
            v-else
            class="flex items-center gap-1"
          >
            <AppImage
              :src="tab.image"
              size="16px"
              contain
              class="icon-bg"
            />
            <span class="capitalize text-rui-text-secondary">
              {{ tab.name }}
            </span>
          </div>
        </RuiTab>
      </RuiTabs>
      <RuiDivider class="mb-4" />
      <RuiTabItems v-model="rpcSettingTab">
        <RuiTabItem
          v-for="tab in rpcSettingTabs"
          :key="isChain(tab) ? tab.chain : tab.id"
        >
          <Component
            :is="tab.component"
            v-if="isChain(tab)"
            ref="evmRpcNodeManagerRef"
            :chain="tab.chain"
          />
          <Component
            :is="tab.component"
            v-else
          />
        </RuiTabItem>
      </RuiTabItems>
    </div>
  </div>
</template>
