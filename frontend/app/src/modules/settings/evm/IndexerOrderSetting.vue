<script setup lang="ts">
import type { ChainItem } from '@/modules/settings/evm/evm-indexer-utils';
import IndexerTabLabel from '@/modules/settings/evm/IndexerTabLabel.vue';
import { useEvmIndexerOrder } from '@/modules/settings/evm/use-evm-indexer-order';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';

defineProps<{
  id?: string;
}>();

defineSlots<{
  footer: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const showChainMenu = ref<boolean>(false);

const {
  addChain,
  availableChainItems,
  availableIndexers,
  chainError,
  chainOrders,
  chainSuccess,
  chainWarnings,
  currentOrder,
  defaultError,
  defaultOrder,
  defaultSuccess,
  missingApiKeyIndexer,
  modelActiveTab,
  primaryIndexerService,
  removeChain,
  tabs,
  updateChainOrder,
  updateDefaultOrder,
} = useEvmIndexerOrder();

async function onAddChain(chain: ChainItem): Promise<void> {
  set(showChainMenu, false);
  await addChain(chain);
}

async function navigateToApiKeys(): Promise<void> {
  const service = primaryIndexerService();
  if (!service)
    return;

  await router.push({ name: '/api-keys/external/', query: { service } });
}
</script>

<template>
  <div
    :id="id"
    data-testid="indexer-order-setting"
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
          v-model="modelActiveTab"
          color="primary"
          class="flex-1 !h-auto overflow-hidden"
          data-testid="indexer-tabs"
        >
          <RuiTab
            v-for="tab in tabs"
            :key="tab.id"
            :value="tab.id"
            data-testid="indexer-tab"
            :data-key="tab.id"
          >
            <IndexerTabLabel
              :tab="tab"
              @remove="removeChain($event)"
            />
          </RuiTab>
        </RuiTabs>

        <RuiMenu
          v-model="showChainMenu"
          :options="{ placement: 'bottom-end' }"
        >
          <template #activator="{ attrs }">
            <RuiButton
              color="primary"
              variant="outlined"
              v-bind="attrs"
              data-testid="add-chain-button"
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
            data-testid="chain-menu"
          >
            <RuiButton
              v-for="chain in availableChainItems"
              :key="chain.id"
              variant="list"
              class="w-full"
              data-testid="chain-menu-item"
              :data-key="chain.id"
              @click="onAddChain(chain)"
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
        data-testid="missing-api-key-alert"
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
        v-for="warning in chainWarnings"
        :key="warning"
        type="warning"
        class="mb-4"
        data-testid="chain-warning-alert"
      >
        {{ t(warning) }}
      </RuiAlert>

      <RuiTabItems v-model="modelActiveTab">
        <RuiTabItem
          v-for="tab in tabs"
          :key="tab.id"
          :value="tab.id"
        >
          <PrioritizedList
            v-if="tab.isDefault"
            data-testid="default-indexer-order"
            :model-value="defaultOrder"
            :all-items="availableIndexers"
            :status="{ error: defaultError, success: defaultSuccess }"
            :item-data-name="t('evm_settings.indexer.data_name')"
            :disable-delete="defaultOrder.length <= 1"
            @update:model-value="updateDefaultOrder($event)"
          >
            <template #title>
              {{ t('evm_settings.indexer.default_order') }}
            </template>
          </PrioritizedList>
          <PrioritizedList
            v-else
            data-testid="chain-indexer-order"
            :data-key="tab.id"
            :model-value="chainOrders[tab.id] ?? []"
            :all-items="availableIndexers"
            :status="{ error: chainError, success: chainSuccess }"
            :item-data-name="t('evm_settings.indexer.data_name')"
            :disable-delete="(chainOrders[tab.id]?.length ?? 0) <= 1"
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
