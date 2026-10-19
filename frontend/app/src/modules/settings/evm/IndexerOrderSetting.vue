<script setup lang="ts">
import type { PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import { type ChainItem, getAvailableIndexersForChain, type TabItem } from '@/modules/settings/evm/evm-indexer-utils';
import IndexerAddMenu from '@/modules/settings/evm/IndexerAddMenu.vue';
import { useEvmIndexerOrder } from '@/modules/settings/evm/use-evm-indexer-order';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';
import PrioritizedListEntry from '@/modules/shell/components/PrioritizedListEntry.vue';

defineProps<{
  id?: string;
}>();

defineSlots<{
  footer: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const showChainMenu = ref<boolean>(false);
const editorOpen = ref<boolean>(false);

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

/** The scope the editor dialog is open on, Default or one chain's override. */
const editedTab = computed<TabItem | undefined>(() => get(tabs).find(tab => tab.id === get(modelActiveTab)));

/** Each row reads its own scope's order, so every override stays visible without switching to it. */
function orderOf(tab: TabItem): PrioritizedListId[] {
  return tab.isDefault ? get(defaultOrder) : (get(chainOrders)[tab.id] ?? []);
}

/**
 * The last save's outcome, shown in the footer beside Done: a line there never moves the list,
 * where an alert under it pushed the dialog around on every reorder.
 */
const editorStatus = computed<{ error: string; success: string }>(() => {
  if (get(editedTab)?.isDefault)
    return { error: get(defaultError), success: get(defaultSuccess) };
  return { error: get(chainError), success: get(chainSuccess) };
});

/**
 * The indexers the open scope could still use. Adding happens from the footer rather than a search
 * row above the list, so the rows never shift when one is removed and the add control appears.
 */
const addableIndexers = computed<PrioritizedListId[]>(() => get(availableIndexers).itemIdsNotIn(get(currentOrder)));

function addIndexer(indexer: PrioritizedListId): void {
  const tab = get(editedTab);
  if (!tab)
    return;
  const order = [...get(currentOrder), indexer];
  if (tab.isDefault)
    updateDefaultOrder(order);
  else
    updateChainOrder(tab.id, order);
}

/** Every indexer's icon, whichever scope it appears in. */
const allIndexers = getAvailableIndexersForChain(null);

function indexerData(indexer: PrioritizedListId): PrioritizedListItemData<PrioritizedListId> {
  return allIndexers.itemDataForId(indexer) ?? { identifier: indexer };
}

function openEditor(tab: TabItem): void {
  set(modelActiveTab, tab.id);
  set(editorOpen, true);
}

async function onAddChain(chain: ChainItem): Promise<void> {
  set(showChainMenu, false);
  await addChain(chain);
  set(editorOpen, true);
}

async function navigateToApiKeys(): Promise<void> {
  const service = primaryIndexerService();
  if (!service)
    return;

  set(editorOpen, false);
  await router.push({ name: '/api-keys/external/', query: { service } });
}
</script>

<template>
  <div
    :id="id"
    class="flex flex-col"
    data-testid="indexer-order-setting"
  >
    <div class="flex items-start justify-between gap-4 pb-4 border-b border-rui-divider">
      <SettingCategoryHeader class="flex-1">
        <template #title>
          {{ t('evm_settings.indexer.title') }}
        </template>
        <template #subtitle>
          {{ t('evm_settings.indexer.subtitle') }}
        </template>
      </SettingCategoryHeader>

      <RuiMenu
        v-model="showChainMenu"
        :options="{ placement: 'bottom-end' }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            color="primary"
            size="sm"
            class="shrink-0"
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
          class="max-h-75 overflow-y-auto"
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

    <div
      class="flex flex-col between:border-t between:border-rui-divider"
      data-testid="indexer-tabs"
    >
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="flex flex-wrap items-center gap-x-4 gap-y-2 py-2.5"
        data-testid="indexer-tab"
        :data-key="tab.id"
      >
        <div class="flex items-center gap-2 w-48 shrink-0 text-sm font-medium text-rui-text">
          <RuiIcon
            v-if="tab.isDefault"
            name="lu-globe"
            size="20"
            class="text-rui-text-secondary"
          />
          <ChainIcon
            v-else
            :chain="tab.id"
            size="20px"
          />
          <span class="truncate">
            {{ tab.isDefault ? t('evm_settings.indexer.default_tab') : tab.name }}
          </span>
        </div>

        <ol class="flex flex-1 min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
          <li
            v-for="(indexer, index) in orderOf(tab)"
            :key="indexer"
            class="flex items-center gap-1.5"
          >
            <RuiIcon
              v-if="index > 0"
              name="lu-arrow-right"
              size="14"
              class="text-rui-text-disabled"
            />
            <PrioritizedListEntry
              :data="indexerData(indexer)"
              size="16px"
              class="gap-1.5!"
            />
          </li>
        </ol>

        <div class="flex items-center gap-1 ml-auto transition-opacity [div:not(:hover)>&:not(:focus-within)]:opacity-0 motion-reduce:transition-none">
          <RuiButton
            variant="text"
            size="sm"
            color="primary"
            data-testid="edit-indexer-order"
            :data-key="tab.id"
            @click="openEditor(tab)"
          >
            {{ t('common.actions.edit') }}
          </RuiButton>
          <span
            v-if="tab.isDefault"
            class="size-6"
          />
          <RuiTooltip
            v-else
            :options="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                variant="text"
                icon
                size="sm"
                class="text-rui-text-secondary!"
                :aria-label="t('evm_settings.indexer.remove_chain')"
                data-testid="remove-chain"
                :data-key="tab.id"
                @click="removeChain(tab.id)"
              >
                <RuiIcon
                  name="lu-x"
                  size="16"
                />
              </RuiButton>
            </template>
            {{ t('evm_settings.indexer.remove_chain') }}
          </RuiTooltip>
        </div>
      </div>
    </div>

    <RuiDialog
      v-model="editorOpen"
      max-width="640"
      :class-names="{ content: 'top-[12vh]! translate-y-0!' }"
    >
      <RuiCard v-if="editedTab">
        <template #header>
          {{ editedTab.isDefault
            ? t('evm_settings.indexer.default_order')
            : t('evm_settings.indexer.chain_order', { chain: editedTab.name }) }}
        </template>

        <div class="flex flex-col gap-4">
          <div
            class="h-50 overflow-y-auto"
            data-testid="indexer-order-list"
          >
            <PrioritizedList
              v-if="editedTab.isDefault"
              data-testid="default-indexer-order"
              variant="flat"
              dense
              disable-add
              :model-value="defaultOrder"
              :all-items="availableIndexers"
              :item-data-name="t('evm_settings.indexer.data_name')"
              :disable-delete="defaultOrder.length <= 1"
              @update:model-value="updateDefaultOrder($event)"
            />
            <PrioritizedList
              v-else
              data-testid="chain-indexer-order"
              variant="flat"
              dense
              disable-add
              :data-key="editedTab.id"
              :model-value="chainOrders[editedTab.id] ?? []"
              :all-items="availableIndexers"
              :item-data-name="t('evm_settings.indexer.data_name')"
              :disable-delete="(chainOrders[editedTab.id]?.length ?? 0) <= 1"
              @update:model-value="updateChainOrder(editedTab.id, $event)"
            />
          </div>

          <RuiAlert
            v-if="currentOrder.length === 0"
            type="warning"
          >
            {{ t('evm_settings.indexer.no_indexers_warning') }}
          </RuiAlert>

          <RuiAlert
            v-else-if="chainWarnings.length > 0 || missingApiKeyIndexer"
            :type="chainWarnings.length > 0 ? 'warning' : 'info'"
            :data-testid="chainWarnings.length > 0 ? 'chain-warning-alert' : 'missing-api-key-alert'"
          >
            <div class="flex flex-col gap-3">
              <p
                v-for="warning in chainWarnings"
                :key="warning"
              >
                {{ t(warning) }}
              </p>
              <p v-if="chainWarnings.length === 0">
                {{ t('evm_settings.indexer.api_key_missing_alert', { indexer: missingApiKeyIndexer }) }}
              </p>
              <RuiButton
                v-if="missingApiKeyIndexer"
                :color="chainWarnings.length > 0 ? 'warning' : 'info'"
                size="sm"
                class="self-start"
                data-testid="enter-api-key"
                @click="navigateToApiKeys()"
              >
                {{ t('evm_settings.indexer.enter_api_key') }}
              </RuiButton>
            </div>
          </RuiAlert>
        </div>

        <template #footer>
          <IndexerAddMenu
            v-if="addableIndexers.length > 0"
            :items="addableIndexers.map(indexerData)"
            @add="addIndexer($event)"
          />
          <span
            class="grow truncate text-sm"
            :class="editorStatus.error ? 'text-rui-error' : 'text-rui-success'"
            role="status"
            data-testid="indexer-editor-status"
          >
            {{ editorStatus.error || editorStatus.success }}
          </span>
          <RuiButton
            color="primary"
            data-testid="indexer-editor-done"
            @click="editorOpen = false"
          >
            {{ t('common.actions.done') }}
          </RuiButton>
        </template>
      </RuiCard>
    </RuiDialog>
    <slot name="footer" />
  </div>
</template>
