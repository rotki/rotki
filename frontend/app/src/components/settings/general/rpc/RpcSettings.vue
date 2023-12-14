<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type AsyncComponent, type Ref } from 'vue';

const { t } = useI18n();

interface RpcSettingTab {
  chain: Blockchain;
  component: AsyncComponent;
}

const rpcSettingTab: Ref<number> = ref(0);

const { txEvmChains } = useSupportedChains();
const evmChainTabs = useArrayMap(txEvmChains, chain => {
  assert(isOfEnum(Blockchain)(chain.id));
  return {
    chain: chain.id,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/EvmRpcNodeManager.vue')
    )
  } satisfies RpcSettingTab;
});

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
  <RuiCard class="mt-8">
    <template #header>
      {{ t('general_settings.rpc_node_setting.title') }}
    </template>

    <div>
      <RuiTabs v-model="rpcSettingTab" color="primary">
        <RuiTab v-for="tab in rpcSettingTabs" :key="tab.chain">
          <ChainDisplay :chain="tab.chain" dense />
        </RuiTab>
      </RuiTabs>
      <RuiDivider class="mb-4" />
      <RuiTabItems v-model="rpcSettingTab">
        <template #default>
          <RuiTabItem v-for="tab in rpcSettingTabs" :key="tab.chain">
            <template #default>
              <Component :is="tab.component" :chain="tab.chain" />
            </template>
          </RuiTabItem>
        </template>
      </RuiTabItems>
    </div>
  </RuiCard>
</template>
