<script setup lang="ts">
import type { Blockchain } from '@rotki/common';
import BlockchainRpcNodeFormDialog from '@/modules/settings/general/rpc/BlockchainRpcNodeFormDialog.vue';
import RpcNodeStatusCell from '@/modules/settings/general/rpc/RpcNodeStatusCell.vue';
import RpcReconnectButton from '@/modules/settings/general/rpc/RpcReconnectButton.vue';
import { useBlockchainRpcNodeManager } from '@/modules/settings/general/rpc/use-blockchain-rpc-node-manager';
import RowActions from '@/modules/shell/components/RowActions.vue';
import SimpleTable from '@/modules/shell/components/SimpleTable.vue';

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
                :class-names="{ content: 'flex items-center gap-1 font-medium' }"
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
              data-testid="node-active"
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
    v-model="modelState"
    :chains="chains"
    @complete="onDialogComplete()"
  />
</template>
