<script setup lang="ts">
import type BlockchainRpcNodeManager from '@/modules/settings/general/rpc/BlockchainRpcNodeManager.vue';
import type SimpleRpcNodeManager from '@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue';
import { startPromise } from '@shared/utils';
import RpcSettingOption from '@/modules/settings/general/rpc/RpcSettingOption.vue';
import { isChainTab, tabKey, useRpcSettingsTabs } from '@/modules/settings/general/rpc/use-rpc-settings-tabs';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';

const BlockchainRpcNodeManagerAsync = defineAsyncComponent(() => import('@/modules/settings/general/rpc/BlockchainRpcNodeManager.vue'));
const SimpleRpcNodeManagerAsync = defineAsyncComponent(() => import('@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue'));

const { t } = useI18n({ useScope: 'global' });
const { isMdAndUp } = useBreakpoint();

const {
  selectedKey,
  rpcSettingTabs,
  evmRailOptions,
  otherRailOptions,
  allRailOptions,
  firstOtherKey,
  canAddNode,
  selectTab,
} = useRpcSettingsTabs();

const evmRpcNodeManagerRef = useTemplateRef<InstanceType<typeof BlockchainRpcNodeManager | typeof SimpleRpcNodeManager>[]>('evmRpcNodeManagerRef');
const railRef = useTemplateRef<HTMLDivElement>('railRef');

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

onMounted(() => scrollActiveIntoView());
watch(selectedKey, () => scrollActiveIntoView());
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
            <BlockchainRpcNodeManagerAsync
              v-if="isChainTab(tab) && !tab.setting"
              ref="evmRpcNodeManagerRef"
              :chain="tab.chain"
            />
            <SimpleRpcNodeManagerAsync
              v-else-if="tab.setting"
              ref="evmRpcNodeManagerRef"
              :setting="tab.setting"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
