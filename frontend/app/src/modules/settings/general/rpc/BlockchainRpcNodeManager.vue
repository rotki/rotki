<script setup lang="ts">
import type { Blockchain } from '@rotki/common';
import BlockchainRpcNodeFormDialog from '@/modules/settings/general/rpc/BlockchainRpcNodeFormDialog.vue';
import RpcNodeStatusCell from '@/modules/settings/general/rpc/RpcNodeStatusCell.vue';
import RpcReconnectButton from '@/modules/settings/general/rpc/RpcReconnectButton.vue';
import { useBlockchainRpcNodeManager } from '@/modules/settings/general/rpc/use-blockchain-rpc-node-manager';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { chain, chains } = defineProps<{
  chain: Blockchain;
  /** Every chain that holds a node list, which the add dialog offers a provider key across. */
  chains: string[];
}>();

const emit = defineEmits<{
  complete: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  addNewRpcNode,
  anyDisconnected,
  editRpcNode,
  getNodeStatus,
  isEtherscan,
  loadError,
  loading,
  loadNodes,
  modelState,
  nodes,
  onActiveChange,
  reConnect,
  reconnecting,
  showDeleteConfirmation,
} = useBlockchainRpcNodeManager(() => chain);

onMounted(async () => {
  await loadNodes();
});

/** A save may have been a provider fan-out, which changes more than this chain's list. */
async function onDialogComplete(): Promise<void> {
  await loadNodes();
  emit('complete');
}

defineExpose({
  addNewRpcNode,
  loadNodes,
});
</script>

<template>
  <RuiTable
    class="bg-white dark:bg-transparent"
    :loading="loading"
    :error="loadError"
    :error-title="t('evm_rpc_node_manager.loading_error.title', { chain })"
    :retry-text="t('common.actions.retry')"
    :empty="nodes.length === 0 ? { label: t('evm_rpc_node_manager.no_nodes') } : false"
    @retry="loadNodes()"
  >
    <thead>
      <tr>
        <th>{{ t('evm_rpc_node_manager.node') }}</th>
        <th class="whitespace-nowrap text-right">
          {{ t('evm_rpc_node_manager.node_weight') }}
        </th>
        <th class="whitespace-nowrap">
          <div class="flex items-center gap-2">
            <div class="w-6">
              <RpcReconnectButton
                v-if="anyDisconnected"
                :disabled="reconnecting"
                :tooltip="t('evm_rpc_node_manager.reconnect.all')"
                data-testid="reconnect-all"
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
        <td class="max-w-0 w-full">
          <div class="flex gap-3 items-center min-w-0">
            <RuiTooltip
              :options="{ placement: 'top' }"
              :open-delay="400"
              class="shrink-0"
            >
              <template #activator>
                <RuiIcon
                  :name="item.owned ? 'lu-user' : 'lu-earth'"
                  size="18"
                  class="text-rui-text-secondary"
                />
              </template>
              <span>{{ item.owned ? t('evm_rpc_node_manager.private_node') : t('evm_rpc_node_manager.public_node') }}</span>
            </RuiTooltip>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-medium truncate">
                  {{ item.name }}
                </span>
                <span
                  v-if="item.isArchive"
                  class="shrink-0 rounded-sm bg-rui-primary/10 px-1.5 text-caption-2 font-medium leading-4 tracking-normal text-rui-primary"
                >
                  {{ t('evm_rpc_node_manager.archive_node') }}
                </span>
              </div>
              <div
                class="text-rui-text-secondary text-xs truncate min-h-4"
                :title="isEtherscan(item) ? undefined : item.endpoint"
              >
                {{ !isEtherscan(item) ? item.endpoint : t('evm_rpc_node_manager.etherscan') }}
              </div>
            </div>
          </div>
        </td>
        <td class="whitespace-nowrap text-right tabular-nums">
          <span v-if="!item.owned">
            {{
              t('evm_rpc_node_manager.weight', {
                weight: item.weight,
              })
            }}
          </span>
        </td>
        <td class="whitespace-nowrap">
          <RpcNodeStatusCell
            :status="getNodeStatus(item)"
            :active="item.active"
            :cooldown-until="item.cooldownUntil"
            :reconnecting="reconnecting"
            @reconnect="reConnect(item.identifier)"
          />
        </td>
        <td class="w-px">
          <div class="flex items-center gap-2 justify-end">
            <RuiSwitch
              color="primary"
              hide-details
              class="mr-2"
              :model-value="item.active"
              :disabled="isEtherscan(item)"
              data-testid="node-active"
              @update:model-value="onActiveChange($event, item)"
            />
            <RowActions
              class="transition-opacity [tr:not(:hover)_&:not(:focus-within)]:opacity-0 motion-reduce:transition-none"
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
  </RuiTable>
  <BlockchainRpcNodeFormDialog
    v-model="modelState"
    :chains="chains"
    @complete="onDialogComplete()"
  />
</template>
