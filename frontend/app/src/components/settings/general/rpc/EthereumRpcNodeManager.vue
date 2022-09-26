<template>
  <card outlined-body class="mt-8">
    <template #title> {{ tc('ethereum_rpc_node_manager.title') }} </template>
    <v-list max-height="300px" :class="$style.list" three-line class="py-0">
      <template v-for="(item, index) in nodes">
        <v-divider v-if="index !== 0" :key="index" />
        <v-list-item :key="item.name" data-cy="ethereum-node" class="px-2">
          <div class="mr-2 pa-4 text-center d-flex flex-column align-center">
            <div>
              <v-tooltip v-if="!item.owned" top open-delay="400">
                <template #activator="{ on, attrs }">
                  <v-icon v-bind="attrs" v-on="on"> mdi-earth </v-icon>
                </template>
                <span>{{ tc('ethereum_rpc_node_manager.public_node') }}</span>
              </v-tooltip>
              <v-tooltip v-else>
                <template #activator="{ on, attrs }">
                  <v-icon v-bind="attrs" v-on="on">mdi-account-network</v-icon>
                </template>
                <span>{{ tc('ethereum_rpc_node_manager.private_node') }}</span>
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
                  {{ tc('ethereum_rpc_node_manager.connected.true') }}
                </span>
              </v-tooltip>
              <v-tooltip v-else top open-delay="400">
                <template #activator="{ on, attrs }">
                  <v-icon v-bind="attrs" small color="red" v-on="on">
                    mdi-wifi-off
                  </v-icon>
                </template>
                <span>
                  {{ tc('ethereum_rpc_node_manager.connected.false') }}
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
              <div v-else>{{ tc('ethereum_rpc_node_manager.etherscan') }}</div>
              <div class="mt-1" :class="$style.weight">
                <span v-if="!item.owned">
                  {{
                    tc('ethereum_rpc_node_manager.weight', 0, {
                      weight: item.weight
                    })
                  }}
                </span>
                <span v-else>
                  {{ tc('ethereum_rpc_node_manager.private_node_hint') }}
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
          <v-list-item-action :class="$style.centered">
            <v-row align="center" justify="center">
              <v-col>
                <row-action
                  :delete-tooltip="
                    tc('ethereum_rpc_node_manager.delete_tooltip')
                  "
                  :delete-disabled="isEtherscan(item)"
                  :edit-tooltip="tc('ethereum_rpc_node_manager.edit_tooltip')"
                  @edit-click="edit(item)"
                  @delete-click="confirmDelete = item"
                />
              </v-col>
            </v-row>
          </v-list-item-action>
        </v-list-item>
      </template>
    </v-list>
    <template #buttons>
      <v-btn
        depressed
        color="primary"
        data-cy="add-node"
        @click="showForm = true"
      >
        {{ tc('ethereum_rpc_node_manager.add_button') }}
      </v-btn>
    </template>
    <big-dialog
      :display="showForm"
      :title="tc('ethereum_rpc_node_manager.add_dialog.title')"
      :primary-action="tc('common.actions.save')"
      :secondary-action="tc('common.actions.cancel')"
      :action-disabled="!valid || loading"
      :loading="loading"
      @confirm="save()"
      @cancel="clear()"
    >
      <rpc-node-form
        v-model="selectedNode"
        :is-etherscan="isEdit && isEtherscan(selectedNode)"
        :error-messages="errors"
        @update:valid="updateValid($event)"
      />
    </big-dialog>
    <confirm-dialog
      :title="tc('ethereum_rpc_node_manager.confirm.title')"
      :display="!!confirmDelete"
      :message="
        tc('ethereum_rpc_node_manager.confirm.message', 0, {
          node: confirmDelete?.name,
          endpoint: confirmDelete?.endpoint
        })
      "
      @confirm="deleteNode"
      @cancel="confirmDelete = null"
    />
  </card>
</template>

<script setup lang="ts">
import { omit } from 'lodash';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RowAction from '@/components/helper/RowActions.vue';
import RpcNodeForm from '@/components/settings/general/rpc/RpcNodeForm.vue';
import { deserializeApiErrorMessage } from '@/services/converters';
import { useEthNodesApi } from '@/services/settings/eth-nodes-api';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import { usePeriodicStore } from '@/store/session/periodic';
import {
  EthereumRpcNode,
  EthereumRpcNodeList,
  getPlaceholderNode
} from '@/types/settings';
import { assert } from '@/utils/assertions';

const nodes = ref<EthereumRpcNodeList>([]);
const showForm = ref(false);
const valid = ref(false);
const loading = ref(false);
const isEdit = ref(false);
const selectedNode = ref<EthereumRpcNode>(getPlaceholderNode());
const confirmDelete = ref<EthereumRpcNode | null>(null);
const errors = ref<Record<string, string[] | string>>({});

const { notify } = useNotifications();
const { setMessage } = useMessageStore();
const { tc } = useI18n();

const { connectedEthNodes } = storeToRefs(usePeriodicStore());
const api = useEthNodesApi();

async function loadNodes(): Promise<void> {
  try {
    set(nodes, await api.fetchEthereumNodes());
  } catch (e: any) {
    notify({
      title: tc('ethereum_rpc_node_manager.loading_error.title'),
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
      await api.editEthereumNode(node);
    } else {
      await api.addEthereumNode(omit(node, 'identifier'));
    }
    await loadNodes();
  } catch (e: any) {
    const errorTitle = editing
      ? tc('ethereum_rpc_node_manager.edit_error.title')
      : tc('ethereum_rpc_node_manager.add_error.title');
    const messages = deserializeApiErrorMessage(e.message);
    if (messages) {
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
  set(selectedNode, getPlaceholderNode());
  set(isEdit, false);
};

const edit = (item: EthereumRpcNode) => {
  set(isEdit, true);
  set(showForm, true);
  set(selectedNode, item);
};

const deleteNode = async () => {
  try {
    let node = get(confirmDelete);
    assert(node);
    const identifier = node.identifier;
    set(confirmDelete, null);
    await api.deleteEthereumNode(identifier);
    await loadNodes();
  } catch (e: any) {
    setMessage({
      title: tc('ethereum_rpc_node_manager.delete_error.title'),
      description: e.message,
      success: false
    });
  }
};

const updateValid = (isValid: boolean) => {
  set(valid, isValid);
  set(errors, {});
};

const onActiveChange = async (active: boolean, node: EthereumRpcNode) => {
  const state = { ...node, active };
  try {
    await api.editEthereumNode(state);
    await loadNodes();
  } catch (e: any) {
    setMessage({
      title: tc('ethereum_rpc_node_manager.activate_error.title', 0, {
        node: node.name
      }),
      description: e.message,
      success: false
    });
  }
};

const isEtherscan = (item: EthereumRpcNode) => item.name === 'etherscan';

const isNodeConnected = (item: EthereumRpcNode): boolean => {
  return get(connectedEthNodes).includes(item.name) || isEtherscan(item);
};
</script>

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
