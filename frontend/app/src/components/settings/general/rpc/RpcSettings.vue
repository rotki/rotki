<script setup lang="ts">
import type { Component } from 'vue';
import type BlockchainRpcNodeManager from '@/components/settings/general/rpc/BlockchainRpcNodeManager.vue';
import type SimpleRpcNodeManager from '@/components/settings/general/rpc/simple/SimpleRpcNodeManager.vue';
import { assert, Blockchain } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { isOfEnum } from '@/utils';

const { t } = useI18n({ useScope: 'global' });

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

const rpcSettingTab = ref<number>(0);
const evmRpcNodeManagerRef = ref<InstanceType<typeof BlockchainRpcNodeManager | typeof SimpleRpcNodeManager>[]>();

const { txEvmChains } = useSupportedChains();
const evmChainTabs = useArrayMap(txEvmChains, (chain) => {
  assert(isOfEnum(Blockchain)(chain.id));
  return {
    chain: chain.id,
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/BlockchainRpcNodeManager.vue')),
  } satisfies RpcSettingTab;
});

const rpcSettingTabs = computed<RpcSettingTab[]>(() => [
  ...get(evmChainTabs),
  {
    // Solana behaves like EVM RPC nodes in UI/API
    chain: Blockchain.SOLANA,
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/BlockchainRpcNodeManager.vue')),
  },
  {
    chain: Blockchain.KSM,
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/simple/SimpleRpcNodeManager.vue')),
    setting: 'ksmRpcEndpoint',
  },
  {
    chain: Blockchain.DOT,
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/simple/SimpleRpcNodeManager.vue')),
    setting: 'dotRpcEndpoint',
  },
  {
    component: defineAsyncComponent(() => import('@/components/settings/general/rpc/simple/SimpleRpcNodeManager.vue')),
    id: 'eth_consensus_layer',
    image: './assets/images/protocols/ethereum.svg',
    name: 'ETH Beacon Node',
    setting: 'beaconRpcEndpoint',
  },
]);

function isChain(item: RpcSettingTab): item is ChainRpcSettingTab {
  return 'chain' in item;
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
        color="primary"
        data-cy="add-node"
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
        </RuiTabItem>
      </RuiTabItems>
    </div>
  </div>
</template>
