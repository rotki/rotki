<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type AsyncComponent, type Ref } from 'vue';

const { tc } = useI18n();

interface RpcSettingTab {
  chain: Blockchain;
  component: AsyncComponent;
}

const rpcSettingTab: Ref<number> = ref(0);

const rpcSettingTabs: RpcSettingTab[] = [
  {
    chain: Blockchain.ETH,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/EthRpcSetting.vue')
    )
  },
  {
    chain: Blockchain.OPTIMISM,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/OptimismRpcSetting.vue')
    )
  },
  {
    chain: Blockchain.KSM,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/KsmRpcSetting.vue')
    )
  },
  {
    chain: Blockchain.DOT,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/DotRpcSetting.vue')
    )
  }
];
</script>

<template>
  <card class="mt-8">
    <template #title>
      {{ tc('general_settings.rpc_node_setting.title') }}
    </template>

    <div>
      <v-tabs v-model="rpcSettingTab">
        <v-tab v-for="tab in rpcSettingTabs" :key="tab.chain">
          <chain-display :chain="tab.chain" dense />
        </v-tab>
      </v-tabs>
      <v-divider />
      <v-tabs-items v-model="rpcSettingTab">
        <v-tab-item v-for="tab in rpcSettingTabs" :key="tab.chain" class="pt-8">
          <component :is="tab.component" />
        </v-tab-item>
      </v-tabs-items>
    </div>
  </card>
</template>
