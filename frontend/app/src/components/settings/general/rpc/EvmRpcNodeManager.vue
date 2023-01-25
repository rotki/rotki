<script setup lang="ts">
import { omit } from 'lodash';
import { Blockchain } from '@rotki/common/lib/blockchain';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RowAction from '@/components/helper/RowActions.vue';
import RpcNodeForm from '@/components/settings/general/rpc/RpcNodeForm.vue';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { usePeriodicStore } from '@/store/session/periodic';
import {
  type EvmRpcNode,
  type EvmRpcNodeList,
  getPlaceholderNode
} from '@/types/settings';
import { useConfirmStore } from '@/store/confirm';
import { ApiValidationError } from '@/types/api/errors';

const props = withDefaults(
  defineProps<{
    chain?: Blockchain;
  }>(),
  {
    chain: Blockchain.ETH
  }
);

const { chain } = toRefs(props);

const nodes = ref<EvmRpcNodeList>([]);
const showForm = ref(false);
const valid = ref(false);
const loading = ref(false);
const isEdit = ref(false);
const selectedNode = ref<EvmRpcNode>(getPlaceholderNode(get(chain)));
const errors = ref<Record<string, string[] | string>>({});

const { notify } = useNotificationsStore();
const { setMessage } = useMessageStore();
const { tc } = useI18n();

const { connectedEthNodes } = storeToRefs(usePeriodicStore());
const api = useEvmNodesApi(get(chain));

async function loadNodes(): Promise<void> {
  try {
    set(nodes, await api.fetchEvmNodes());
  } catch (e: any) {
    notify({
      title: tc('evm_rpc_node_manager.loading_error.title', 0, {
        chain: get(chain)
      }),
      message: e.message
    });
  }
}

onMounted(async () => {
  await loadNodes();
});

const save = async () => {
  const editing = get(isEdit);
  try {
    set(loading, true);
    const node = get(selectedNode);
    if (editing) {
      await api.editEvmNode(node);
    } else {
      await api.addEvmNode(omit(node, 'identifier'));
    }
    await loadNodes();
  } catch (e: any) {
    const chainProp = get(chain);
    const errorTitle = editing
      ? tc('evm_rpc_node_manager.edit_error.title', 0, { chain: chainProp })
      : tc('evm_rpc_node_manager.add_error.title', 0, { chain: chainProp });

    if (e instanceof ApiValidationError) {
      const messages = e.errors;

      set(errors, messages);

      const keys = Object.keys(messages);
      const knownKeys = Object.keys(get(selectedNode));
      const unknownKeys = keys.filter(key => !knownKeys.includes(key));

      if (unknownKeys.length > 0) {
        setMessage({
          title: errorTitle,
          description: unknownKeys
            .map(key => `${key}: ${messages[key]}`)
            .join(', '),
          success: false
        });
      }
    } else {
      setMessage({
        title: errorTitle,
        description: e.message,
        success: false
      });
    }
  } finally {
    set(loading, false);
    clear();
  }
};

const clear = () => {
  set(showForm, false);
  set(selectedNode, getPlaceholderNode(get(chain)));
  set(isEdit, false);
};

const edit = (item: EvmRpcNode) => {
  set(isEdit, true);
  set(showForm, true);
  set(selectedNode, item);
};

const deleteNode = async (node: EvmRpcNode) => {
  try {
    const identifier = node.identifier;
    await api.deleteEvmNode(identifier);
    await loadNodes();
  } catch (e: any) {
    setMessage({
      title: tc('evm_rpc_node_manager.delete_error.title', 0, {
        chain: get(chain)
      }),
      description: e.message,
      success: false
    });
  }
};

const updateValid = (isValid: boolean) => {
  set(valid, isValid);
  set(errors, {});
};

const onActiveChange = async (active: boolean, node: EvmRpcNode) => {
  const state = { ...node, active };
  try {
    await api.editEvmNode(state);
    await loadNodes();
  } catch (e: any) {
    setMessage({
      title: tc('evm_rpc_node_manager.activate_error.title', 0, {
        node: node.name
      }),
      description: e.message,
      success: false
    });
  }
};

const isEtherscan = (item: EvmRpcNode) => item.name === 'etherscan';

const isNodeConnected = (item: EvmRpcNode): boolean => {
  return get(connectedEthNodes).includes(item.name) || isEtherscan(item);
};

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: EvmRpcNode) => {
  const chainProp = get(chain);
  show(
    {
      title: tc('evm_rpc_node_manager.confirm.title', 0, { chain: chainProp }),
      message: tc('evm_rpc_node_manager.confirm.message', 0, {
        node: item.name,
        endpoint: item.endpoint,
        chain: chainProp
      })
    },
    () => deleteNode(item)
  );
};

const css = useCssModule();
</script>

<template>
  <div>
    <v-card outlined>
      <v-list max-height="300px" :class="css.list" three-line class="py-0">
        <template v-for="(item, index) in nodes">
          <v-divider v-if="index !== 0" :key="index" />
          <v-list-item :key="item.name" data-cy="ethereum-node" class="px-2">
            <div class="mr-2 pa-4 text-center d-flex flex-column align-center">
              <div>
                <v-tooltip v-if="!item.owned" top open-delay="400">
                  <template #activator="{ on, attrs }">
                    <v-icon v-bind="attrs" v-on="on"> mdi-earth </v-icon>
                  </template>
                  <span>{{ tc('evm_rpc_node_manager.public_node') }}</span>
                </v-tooltip>
                <v-tooltip v-else>
                  <template #activator="{ on, attrs }">
                    <v-icon v-bind="attrs" v-on="on">
                      mdi-account-network
                    </v-icon>
                  </template>
                  <span>{{ tc('evm_rpc_node_manager.private_node') }}</span>
                </v-tooltip>
              </div>

              <div class="mt-2">
                <v-tooltip v-if="isNodeConnected(item)" top open-delay="400">
                  <template #activator="{ on, attrs }">
                    <v-icon v-bind="attrs" small color="green" v-on="on">
                      mdi-wifi
                    </v-icon>
                  </template>
                  <span>
                    {{ tc('evm_rpc_node_manager.connected.true') }}
                  </span>
                </v-tooltip>
                <v-tooltip v-else top open-delay="400">
                  <template #activator="{ on, attrs }">
                    <v-icon v-bind="attrs" small color="red" v-on="on">
                      mdi-wifi-off
                    </v-icon>
                  </template>
                  <span>
                    {{ tc('evm_rpc_node_manager.connected.false') }}
                  </span>
                </v-tooltip>
              </div>
            </div>

            <v-list-item-content>
              <v-list-item-title class="font-weight-medium">
                {{ item.name }}
              </v-list-item-title>
              <v-list-item-subtitle>
                <div v-if="!isEtherscan(item)">
                  {{ item.endpoint }}
                </div>
                <div v-else>
                  {{ tc('evm_rpc_node_manager.etherscan') }}
                </div>
                <div class="mt-1" :class="css.weight">
                  <span v-if="!item.owned">
                    {{
                      tc('evm_rpc_node_manager.weight', 0, {
                        weight: item.weight
                      })
                    }}
                  </span>
                  <span v-else>
                    {{ tc('evm_rpc_node_manager.private_node_hint') }}
                  </span>
                </div>
              </v-list-item-subtitle>
            </v-list-item-content>
            <v-switch
              value=""
              :input-value="item.active"
              :disabled="isEtherscan(item)"
              @change="onActiveChange($event, item)"
            />
            <v-list-item-action :class="css.centered">
              <v-row align="center" justify="center">
                <v-col>
                  <row-action
                    :delete-tooltip="tc('evm_rpc_node_manager.delete_tooltip')"
                    :delete-disabled="isEtherscan(item)"
                    :edit-tooltip="tc('evm_rpc_node_manager.edit_tooltip')"
                    @edit-click="edit(item)"
                    @delete-click="showDeleteConfirmation(item)"
                  />
                </v-col>
              </v-row>
            </v-list-item-action>
          </v-list-item>
        </template>
      </v-list>
      <big-dialog
        :display="showForm"
        :title="tc('evm_rpc_node_manager.add_dialog.title', 0, { chain })"
        :primary-action="tc('common.actions.save')"
        :secondary-action="tc('common.actions.cancel')"
        :action-disabled="!valid || loading"
        :loading="loading"
        @confirm="save()"
        @cancel="clear()"
      >
        <rpc-node-form
          v-model="selectedNode"
          :chain="chain"
          :is-etherscan="isEdit && isEtherscan(selectedNode)"
          :error-messages="errors"
          @update:valid="updateValid($event)"
        />
      </big-dialog>
    </v-card>

    <div class="pt-8">
      <v-btn
        depressed
        color="primary"
        data-cy="add-node"
        @click="showForm = true"
      >
        {{ tc('evm_rpc_node_manager.add_button') }}
      </v-btn>
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
