<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import camelCase from 'lodash/camelCase';
import {
  type EvmRpcNode,
  type EvmRpcNodeList,
  getPlaceholderNode
} from '@/types/settings';

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

const css = useCssModule();
</script>

<template>
  <div>
    <VCard outlined>
      <VList max-height="300px" :class="css.list" three-line class="py-0">
        <template v-for="(item, index) in nodes">
          <VDivider v-if="index !== 0" :key="index" />
          <VListItem
            :key="index + item.name"
            data-cy="ethereum-node"
            class="px-2"
          >
            <div class="mr-2 pa-4 text-center d-flex flex-column align-center">
              <div>
                <VTooltip v-if="!item.owned" top open-delay="400">
                  <template #activator="{ on, attrs }">
                    <VIcon v-bind="attrs" v-on="on"> mdi-earth </VIcon>
                  </template>
                  <span>{{ t('evm_rpc_node_manager.public_node') }}</span>
                </VTooltip>
                <VTooltip v-else>
                  <template #activator="{ on, attrs }">
                    <VIcon v-bind="attrs" v-on="on">
                      mdi-account-network
                    </VIcon>
                  </template>
                  <span>{{ t('evm_rpc_node_manager.private_node') }}</span>
                </VTooltip>
              </div>

              <div class="mt-2">
                <VTooltip v-if="isNodeConnected(item)" top open-delay="400">
                  <template #activator="{ on, attrs }">
                    <VIcon v-bind="attrs" small color="green" v-on="on">
                      mdi-wifi
                    </VIcon>
                  </template>
                  <span>
                    {{ t('evm_rpc_node_manager.connected.true') }}
                  </span>
                </VTooltip>
                <VTooltip v-else top open-delay="400">
                  <template #activator="{ on, attrs }">
                    <VIcon v-bind="attrs" small color="red" v-on="on">
                      mdi-wifi-off
                    </VIcon>
                  </template>
                  <span>
                    {{ t('evm_rpc_node_manager.connected.false') }}
                  </span>
                </VTooltip>
              </div>
            </div>

            <VListItemContent>
              <VListItemTitle class="font-weight-medium">
                {{ item.name }}
              </VListItemTitle>
              <VListItemSubtitle>
                <div v-if="!isEtherscan(item)">
                  {{ item.endpoint }}
                </div>
                <div v-else>
                  {{ t('evm_rpc_node_manager.etherscan') }}
                </div>
                <div class="mt-1" :class="css.weight">
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
              </VListItemSubtitle>
            </VListItemContent>
            <VSwitch
              value=""
              :input-value="item.active"
              :disabled="isEtherscan(item)"
              @change="onActiveChange($event, item)"
            />
            <VListItemAction :class="css.centered">
              <VRow align="center" justify="center">
                <VCol>
                  <RowActions
                    :delete-tooltip="t('evm_rpc_node_manager.delete_tooltip')"
                    :delete-disabled="isEtherscan(item)"
                    :edit-tooltip="t('evm_rpc_node_manager.edit_tooltip')"
                    @edit-click="edit(item)"
                    @delete-click="showDeleteConfirmation(item)"
                  />
                </VCol>
              </VRow>
            </VListItemAction>
          </VListItem>
        </template>
      </VList>

      <EvmRpcNodeFormDialog
        v-model="selectedNode"
        :chain="chain"
        :chain-name="chainName"
        :edit-mode="editMode"
        :is-etherscan="editMode && isEtherscan(selectedNode)"
        @reset="resetForm()"
      />
    </VCard>

    <div class="pt-8">
      <VBtn
        depressed
        color="primary"
        data-cy="add-node"
        @click="setOpenDialog(true)"
      >
        {{ t('evm_rpc_node_manager.add_button') }}
      </VBtn>
    </div>
  </div>
</template>

<style module lang="scss">
.list {
  overflow-y: auto;
  overflow-x: hidden;
}

.weight {
  font-size: 13px;
}

.centered {
  align-self: center !important;
}
</style>
