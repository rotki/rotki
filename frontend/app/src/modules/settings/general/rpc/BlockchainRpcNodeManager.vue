<script setup lang="ts">
import type { Blockchain } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';
import BlockchainRpcNodeFormDialog from '@/modules/settings/general/rpc/BlockchainRpcNodeFormDialog.vue';
import { NODE_STATUS, type NodeStatus } from '@/modules/settings/general/rpc/rpc-node-status';
import RpcNodeStatusCell from '@/modules/settings/general/rpc/RpcNodeStatusCell.vue';
import RpcReconnectButton from '@/modules/settings/general/rpc/RpcReconnectButton.vue';
import {
  type BlockchainRpcNode,
  type BlockchainRpcNodeList,
  type BlockchainRpcNodeManageState,
  getPlaceholderNode,
} from '@/modules/settings/types/rpc';
import RowActions from '@/modules/shell/components/RowActions.vue';
import SimpleTable from '@/modules/shell/components/SimpleTable.vue';

const { chain } = defineProps<{
  chain: Blockchain;
}>();

const { t } = useI18n({ useScope: 'global' });

const nodes = ref<BlockchainRpcNodeList>([]);
const state = ref<BlockchainRpcNodeManageState>();
const reconnecting = ref<boolean>(false);

const { notify } = useNotificationDispatcher();
const { setMessage } = useMessageStore();

const { connectedNodes, coolingDownNodes, failedToConnect } = storeToRefs(useSessionMetadataStore());
const { show } = useConfirmStore();
const { useChainName } = useSupportedChains();
const api = useEvmNodesApi(() => chain);

const chainName = useChainName(() => chain);
const anyDisconnected = computed(() => get(nodes).some(node => !isNodeConnected(node) && node.active));

async function loadNodes(): Promise<void> {
  try {
    set(nodes, await api.fetchEvmNodes());
  }
  catch (error: unknown) {
    notify({
      message: getErrorMessage(error),
      title: t('evm_rpc_node_manager.loading_error.title', {
        chain,
      }),
    });
  }
}

function editRpcNode(node: BlockchainRpcNode) {
  set(state, {
    mode: 'edit',
    node,
  });
}

function addNewRpcNode() {
  set(state, {
    mode: 'add',
    node: getPlaceholderNode(chain),
  });
}

async function deleteNode(node: BlockchainRpcNode) {
  try {
    const identifier = node.identifier;
    await api.deleteEvmNode(identifier);
    await loadNodes();
  }
  catch (error: unknown) {
    setMessage({
      description: getErrorMessage(error),
      success: false,
      title: t('evm_rpc_node_manager.delete_error.title', {
        chain,
      }),
    });
  }
}

async function onActiveChange(active: boolean, node: BlockchainRpcNode) {
  const state = { ...node, active };
  try {
    await api.editEvmNode(state);
    await loadNodes();
  }
  catch (error: unknown) {
    setMessage({
      description: getErrorMessage(error),
      success: false,
      title: t('evm_rpc_node_manager.activate_error.title', {
        node: node.name,
      }),
    });
  }
}

function isEtherscan(item: BlockchainRpcNode) {
  return !item.endpoint && item.name.includes('etherscan');
}

function isNodeInDataset(dataset: Record<string, string[]>, item: BlockchainRpcNode): boolean {
  const blockchain = camelCase(chain);
  const nodes = dataset?.[blockchain] || [];
  return nodes.includes(item.name);
}

function isNodeConnected(item: BlockchainRpcNode): boolean {
  return isEtherscan(item) || isNodeInDataset(get(connectedNodes), item);
}

function getNodeStatus(item: BlockchainRpcNode): NodeStatus {
  if (isNodeInDataset(get(coolingDownNodes), item)) {
    return NODE_STATUS.COOLING_DOWN;
  }

  if (isNodeConnected(item)) {
    return NODE_STATUS.CONNECTED;
  }

  if (isNodeInDataset(get(failedToConnect), item)) {
    return NODE_STATUS.FAILED;
  }

  return NODE_STATUS.READY;
}

function showDeleteConfirmation(item: BlockchainRpcNode) {
  const chainProp = get(chainName);
  show(
    {
      message: t('evm_rpc_node_manager.confirm.message', {
        chain: chainProp,
        endpoint: item.endpoint,
        node: item.name,
      }),
      title: t('evm_rpc_node_manager.confirm.title', { chain: chainProp }),
    },
    () => deleteNode(item),
  );
}

async function reConnect(identifier?: number) {
  set(reconnecting, true);
  const success = await api.reConnectNode(identifier);
  set(reconnecting, false);

  if (success) {
    await loadNodes();
  }
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
        <th>
          <div class="flex items-center gap-2">
            <div class="w-6">
              <RpcReconnectButton
                v-if="anyDisconnected"
                :disabled="reconnecting"
                :tooltip="t('evm_rpc_node_manager.reconnect.all')"
                @reconnect="reConnect()"
              />
            </div>
            {{ t('evm_rpc_node_manager.connectivity') }}
          </div>
        </th>
        <th />
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="(item, index) in nodes"
        :key="index + item.name"
        class="border-b border-default"
        data-testid="ethereum-node"
      >
        <td>
          <div class="flex gap-3 items-center">
            <RuiTooltip
              v-if="!item.owned"
              :options="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiIcon
                  name="lu-earth"
                  class="text-rui-text-secondary"
                />
              </template>
              <span>{{ t('evm_rpc_node_manager.public_node') }}</span>
            </RuiTooltip>
            <RuiTooltip
              v-else
              :options="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiIcon
                  name="lu-user"
                  class="text-rui-text-secondary"
                />
              </template>
              <span>{{ t('evm_rpc_node_manager.private_node') }}</span>
            </RuiTooltip>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-medium">
                  {{ item.name }}
                </span>
              </div>
              <div class="text-rui-text-secondary text-sm">
                {{ !isEtherscan(item) ? item.endpoint : t('evm_rpc_node_manager.etherscan') }}
              </div>
              <RuiChip
                v-if="item.isArchive"
                size="sm"
                color="primary"
                class="!p-0.5 mt-2"
                content-class="flex items-center gap-1 font-medium"
              >
                <RuiIcon
                  name="lu-check"
                  size="14"
                />
                {{ t('evm_rpc_node_manager.archive_node') }}
              </RuiChip>
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
          <RpcNodeStatusCell
            :status="getNodeStatus(item)"
            :active="item.active"
            :cooldown-until="item.cooldownUntil"
            :reconnecting="reconnecting"
            @reconnect="reConnect(item.identifier)"
          />
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
  <BlockchainRpcNodeFormDialog
    v-model="state"
    @complete="loadNodes()"
  />
</template>
