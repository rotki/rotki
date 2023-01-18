<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Component, type Ref } from 'vue';
import EthRpcSetting from '@/components/settings/general/rpc/EthRpcSetting.vue';
import OptimismRpcSetting from '@/components/settings/general/rpc/OptimismRpcSetting.vue';
import KsmRpcSetting from '@/components/settings/general/rpc/KsmRpcSetting.vue';
import DotRpcSetting from '@/components/settings/general/rpc/DotRpcSetting.vue';

const { tc } = useI18n();

interface RpcSettingTab {
  chain: Blockchain;
  component: Component;
}

const rpcSettingTab: Ref<number> = ref(0);

const rpcSettingTabs: RpcSettingTab[] = [
  {
    chain: Blockchain.ETH,
    component: EthRpcSetting
  },
  {
    chain: Blockchain.OPTIMISM,
    component: OptimismRpcSetting
  },
  {
    chain: Blockchain.KSM,
    component: KsmRpcSetting
  },
  {
    chain: Blockchain.DOT,
    component: DotRpcSetting
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
