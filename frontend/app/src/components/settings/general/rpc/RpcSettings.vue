<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type AsyncComponent, type Ref } from 'vue';

const { t } = useI18n();

interface RpcSettingTab {
  chain: string;
  component: AsyncComponent;
}

const rpcSettingTab: Ref<number> = ref(0);

const { txEvmChains } = useSupportedChains();
const evmChainTabs = useArrayMap(
  txEvmChains,
  chain =>
    ({
      chain: chain.id,
      component: defineAsyncComponent(
        () => import('@/components/settings/general/rpc/EvmRpcNodeManager.vue')
      )
    }) satisfies RpcSettingTab
);

const rpcSettingTabs = computed<RpcSettingTab[]>(() => [
  ...get(evmChainTabs),
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
]);
</script>

<template>
  <Card class="mt-8">
    <template #title>
      {{ t('general_settings.rpc_node_setting.title') }}
    </template>

    <div>
      <VTabs v-model="rpcSettingTab">
        <VTab v-for="tab in rpcSettingTabs" :key="tab.chain">
          <ChainDisplay :chain="tab.chain" dense />
        </VTab>
      </VTabs>
      <VDivider />
      <VTabsItems v-model="rpcSettingTab">
        <VTabItem v-for="tab in rpcSettingTabs" :key="tab.chain" class="pt-8">
          <Component :is="tab.component" :chain="tab.chain" />
        </VTabItem>
      </VTabsItems>
    </div>
  </Card>
</template>
