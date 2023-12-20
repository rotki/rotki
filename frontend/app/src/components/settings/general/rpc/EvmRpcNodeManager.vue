<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { camelCase } from 'lodash-es';
import {
  type EvmRpcNode,
  type EvmRpcNodeList,
  getPlaceholderNode
} from '@/types/settings/rpc';

const props = defineProps<{
  chain: Blockchain;
}>();

const { t } = useI18n();

const { chain } = toRefs(props);

const nodes = ref<EvmRpcNodeList>([]);
const editMode = ref(false);
const selectedNode = ref<EvmRpcNode>(getPlaceholderNode(get(chain)));

const { notify } = useNotificationsStore();
const { setMessage } = useMessageStore();

const { setOpenDialog, closeDialog, setPostSubmitFunc } =
  useEvmRpcNodeForm(chain);

const { connectedNodes } = storeToRefs(usePeriodicStore());
const api = useEvmNodesApi(get(chain));
const { getEvmChainName, getChainName } = useSupportedChains();

const chainName = computed(() => get(getChainName(chain)));

async function loadNodes(): Promise<void> {
  try {
    set(nodes, await api.fetchEvmNodes());
  } catch (e: any) {
    notify({
      title: t('evm_rpc_node_manager.loading_error.title', {
        chain: get(chain)
      }),
      message: e.message
    });
  }
}

onMounted(async () => {
  await loadNodes();
});

const resetForm = () => {
  closeDialog();
  set(selectedNode, getPlaceholderNode(get(chain)));
  set(editMode, false);
};

setPostSubmitFunc(async () => {
  await loadNodes();
  resetForm();
});

const edit = (item: EvmRpcNode) => {
  setOpenDialog(true);
  set(selectedNode, item);
  set(editMode, true);
};

const deleteNode = async (node: EvmRpcNode) => {
  try {
    const identifier = node.identifier;
    await api.deleteEvmNode(identifier);
    await loadNodes();
  } catch (e: any) {
    setMessage({
      title: t('evm_rpc_node_manager.delete_error.title', {
        chain: get(chain)
      }),
      description: e.message,
      success: false
    });
  }
};

const onActiveChange = async (active: boolean, node: EvmRpcNode) => {
  const state = { ...node, active };
  try {
    await api.editEvmNode(state);
    await loadNodes();
  } catch (e: any) {
    setMessage({
      title: t('evm_rpc_node_manager.activate_error.title', {
        node: node.name
      }),
      description: e.message,
      success: false
    });
  }
};

const isEtherscan = (item: EvmRpcNode) =>
  !item.endpoint && item.name.includes('etherscan');

const isNodeConnected = (item: EvmRpcNode): boolean => {
  const blockchain = get(chain);
  const connected = get(connectedNodes);
  const evmChain = camelCase(getEvmChainName(blockchain) ?? '');
  const nodes = evmChain && connected[evmChain] ? connected[evmChain] : [];

  return nodes.includes(item.name) || isEtherscan(item);
};

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: EvmRpcNode) => {
  const chainProp = get(chainName);
  show(
    {
      title: t('evm_rpc_node_manager.confirm.title', { chain: chainProp }),
      message: t('evm_rpc_node_manager.confirm.message', {
        node: item.name,
        endpoint: item.endpoint,
        chain: chainProp
      })
    },
    () => deleteNode(item)
  );
};

onUnmounted(() => {
  disposeEvmRpcNodeComposables();
});
</script>

<template>
  <div>
    <RuiCard no-padding class="overflow-hidden">
      <div class="overflow-auto max-h-[300px]">
        <template v-for="(item, index) in nodes">
          <RuiDivider v-if="index !== 0" :key="index" />
          <div
            :key="index + item.name"
            data-cy="ethereum-node"
            class="px-2 flex items-center"
          >
            <div class="mr-2 p-4 text-center flex flex-col items-center">
              <div>
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
                    <RuiIcon name="user-2-line" />
                  </template>
                  <span>{{ t('evm_rpc_node_manager.private_node') }}</span>
                </RuiTooltip>
              </div>

              <div class="mt-2">
                <RuiTooltip
                  v-if="isNodeConnected(item)"
                  :popper="{ placement: 'top' }"
                  :open-delay="400"
                >
                  <template #activator>
                    <RuiIcon color="success" size="16" name="wifi-line" />
                  </template>
                  <span>
                    {{ t('evm_rpc_node_manager.connected.true') }}
                  </span>
                </RuiTooltip>
                <RuiTooltip
                  v-else
                  :popper="{ placement: 'top' }"
                  :open-delay="400"
                >
                  <template #activator>
                    <RuiIcon color="error" size="16" name="wifi-off-line" />
                  </template>
                  <span>
                    {{ t('evm_rpc_node_manager.connected.false') }}
                  </span>
                </RuiTooltip>
              </div>
            </div>
            <div class="flex-1">
              <div class="font-medium">
                {{ item.name }}
              </div>
              <div class="text-rui-text-secondary">
                <div v-if="!isEtherscan(item)">
                  {{ item.endpoint }}
                </div>
                <div v-else>
                  {{ t('evm_rpc_node_manager.etherscan') }}
                </div>
                <div class="mt-1 text-sm">
                  <span v-if="!item.owned">
                    {{
                      t('evm_rpc_node_manager.weight', {
                        weight: item.weight
                      })
                    }}
                  </span>
                  <span v-else>
                    {{ t('evm_rpc_node_manager.private_node_hint') }}
                  </span>
                </div>
              </div>
            </div>
            <VSwitch
              value=""
              :input-value="item.active"
              :disabled="isEtherscan(item)"
              @change="onActiveChange($event, item)"
            />
            <RowActions
              :delete-tooltip="t('evm_rpc_node_manager.delete_tooltip')"
              :delete-disabled="isEtherscan(item)"
              :edit-tooltip="t('evm_rpc_node_manager.edit_tooltip')"
              @edit-click="edit(item)"
              @delete-click="showDeleteConfirmation(item)"
            />
          </div>
        </template>
      </div>

      <EvmRpcNodeFormDialog
        v-model="selectedNode"
        :chain="chain"
        :chain-name="chainName"
        :edit-mode="editMode"
        :is-etherscan="editMode && isEtherscan(selectedNode)"
        @reset="resetForm()"
      />
    </RuiCard>

    <RuiButton
      class="mt-8"
      color="primary"
      data-cy="add-node"
      @click="setOpenDialog(true)"
    >
      {{ t('evm_rpc_node_manager.add_button') }}
    </RuiButton>
  </div>
</template>
