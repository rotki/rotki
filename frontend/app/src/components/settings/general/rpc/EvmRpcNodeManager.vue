<script setup lang="ts">
import { camelCase } from 'lodash-es';
import {
  type EvmRpcNode,
  type EvmRpcNodeList,
  type EvmRpcNodeManageState,
  getPlaceholderNode,
} from '@/types/settings/rpc';
import type { Blockchain } from '@rotki/common';

const props = defineProps<{
  chain: Blockchain;
}>();

const { t } = useI18n();

const { chain } = toRefs(props);

const nodes = ref<EvmRpcNodeList>([]);
const state = ref<EvmRpcNodeManageState>();

const { notify } = useNotificationsStore();
const { setMessage } = useMessageStore();

const { connectedNodes } = storeToRefs(usePeriodicStore());
const api = useEvmNodesApi(chain);
const { getEvmChainName, getChainName } = useSupportedChains();

const chainName = computed(() => get(getChainName(chain)));

async function loadNodes(): Promise<void> {
  try {
    set(nodes, await api.fetchEvmNodes());
  }
  catch (error: any) {
    notify({
      title: t('evm_rpc_node_manager.loading_error.title', {
        chain: get(chain),
      }),
      message: error.message,
    });
  }
}

function editRpcNode(node: EvmRpcNode) {
  set(state, {
    mode: 'edit',
    node,
  });
}

function addNewRpcNode() {
  set(state, {
    mode: 'add',
    node: getPlaceholderNode(get(chain)),
  });
}

async function deleteNode(node: EvmRpcNode) {
  try {
    const identifier = node.identifier;
    await api.deleteEvmNode(identifier);
    await loadNodes();
  }
  catch (error: any) {
    setMessage({
      title: t('evm_rpc_node_manager.delete_error.title', {
        chain: get(chain),
      }),
      description: error.message,
      success: false,
    });
  }
}

async function onActiveChange(active: boolean, node: EvmRpcNode) {
  const state = { ...node, active };
  try {
    await api.editEvmNode(state);
    await loadNodes();
  }
  catch (error: any) {
    setMessage({
      title: t('evm_rpc_node_manager.activate_error.title', {
        node: node.name,
      }),
      description: error.message,
      success: false,
    });
  }
}

function isEtherscan(item: EvmRpcNode) {
  return !item.endpoint && item.name.includes('etherscan');
}

function isNodeConnected(item: EvmRpcNode): boolean {
  const blockchain = get(chain);
  const connected = get(connectedNodes);
  const evmChain = camelCase(getEvmChainName(blockchain) ?? '');
  const nodes = evmChain && connected[evmChain] ? connected[evmChain] : [];

  return nodes.includes(item.name) || isEtherscan(item);
}

const { show } = useConfirmStore();

function showDeleteConfirmation(item: EvmRpcNode) {
  const chainProp = get(chainName);
  show(
    {
      title: t('evm_rpc_node_manager.confirm.title', { chain: chainProp }),
      message: t('evm_rpc_node_manager.confirm.message', {
        node: item.name,
        endpoint: item.endpoint,
        chain: chainProp,
      }),
    },
    () => deleteNode(item),
  );
}

onMounted(async () => {
  await loadNodes();
});

defineExpose({
  addNewRpcNode,
});
</script>

<template>
  <SimpleTable class="bg-white dark:bg-transparent">
    <thead>
      <tr>
        <th>{{ t('evm_rpc_node_manager.node') }}</th>
        <th>{{ t('evm_rpc_node_manager.node_weight') }}</th>
        <th>{{ t('evm_rpc_node_manager.connectivity') }}</th>
        <th />
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="(item, index) in nodes"
        :key="index + item.name"
        class="border-b border-default"
        data-cy="ethereum-node"
      >
        <td>
          <div class="flex gap-3 items-center">
            <RuiTooltip
              v-if="!item.owned"
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiIcon
                  name="earth-line"
                  class="text-rui-text-secondary"
                />
              </template>
              <span>{{ t('evm_rpc_node_manager.public_node') }}</span>
            </RuiTooltip>
            <RuiTooltip
              v-else
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiIcon
                  name="user-2-line"
                  class="text-rui-text-secondary"
                />
              </template>
              <span>{{ t('evm_rpc_node_manager.private_node') }}</span>
            </RuiTooltip>
            <div>
              <div class="font-medium">
                {{ item.name }}
              </div>
              <div class="text-rui-text-secondary text-sm">
                {{ !isEtherscan(item) ? item.endpoint : t('evm_rpc_node_manager.etherscan') }}
              </div>
            </div>
          </div>
        </td>
        <td>
          <span v-if="!item.owned">
            {{
              t('evm_rpc_node_manager.weight', {
                weight: item.weight,
              })
            }}
          </span>
        </td>
        <td>
          <BadgeDisplay
            v-if="isNodeConnected(item)"
            color="green"
            class="items-center gap-2 !leading-6"
          >
            <RuiIcon
              color="success"
              size="16"
              name="wifi-line"
            />
            <span>
              {{ t('evm_rpc_node_manager.connected.true') }}
            </span>
          </BadgeDisplay>
          <BadgeDisplay
            v-else
            color="red"
            class="items-center gap-2 !leading-6"
          >
            <RuiIcon
              color="error"
              size="16"
              name="wifi-off-line"
            />
            <span>
              {{ t('evm_rpc_node_manager.connected.false') }}
            </span>
          </BadgeDisplay>
        </td>
        <td>
          <div class="flex items-center gap-2 justify-end">
            <RuiSwitch
              color="primary"
              hide-details
              class="mr-4"
              :model-value="item.active"
              :disabled="isEtherscan(item)"
              @update:model-value="onActiveChange($event, item)"
            />
            <RowActions
              :delete-tooltip="t('evm_rpc_node_manager.delete_tooltip')"
              :delete-disabled="isEtherscan(item)"
              :edit-tooltip="t('evm_rpc_node_manager.edit_tooltip')"
              @edit-click="editRpcNode(item)"
              @delete-click="showDeleteConfirmation(item)"
            />
          </div>
        </td>
      </tr>
    </tbody>
  </SimpleTable>
  <EvmRpcNodeFormDialog
    v-model="state"
    @complete="loadNodes()"
  />
</template>
