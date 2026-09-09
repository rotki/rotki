import type { Blockchain } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { camelCase } from 'es-toolkit';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';
import { NODE_STATUS, type NodeStatus } from '@/modules/settings/general/rpc/rpc-node-status';
import {
  type BlockchainRpcNode,
  type BlockchainRpcNodeList,
  type BlockchainRpcNodeManageState,
  getPlaceholderNode,
} from '@/modules/settings/types/rpc';

interface UseBlockchainRpcNodeManagerReturn {
  /** Opens the form on a blank node for this chain. */
  addNewRpcNode: () => void;
  /** Whether any active node is not currently connected, which is what offers "reconnect all". */
  anyDisconnected: ComputedRef<boolean>;
  /** Opens the form on an existing node. */
  editRpcNode: (node: BlockchainRpcNode) => void;
  /** The connectivity a row should show for a node. */
  getNodeStatus: (item: BlockchainRpcNode) => NodeStatus;
  /**
   * Whether a node is the built-in etherscan entry.
   *
   * @remarks
   * It has no endpoint of its own and cannot be deleted or deactivated, so rows use this to
   * disable those controls.
   */
  isEtherscan: (item: BlockchainRpcNode) => boolean;
  /** Reads the chain's nodes, reporting a failure as a notification rather than a message. */
  loadNodes: () => Promise<void>;
  /** The form's node, or undefined while the form is closed. */
  modelState: Ref<BlockchainRpcNodeManageState | undefined>;
  /** The chain's nodes, in the order the backend returns them. */
  nodes: Readonly<Ref<BlockchainRpcNodeList>>;
  /** Activates or deactivates a node, then re-reads the list. */
  onActiveChange: (active: boolean, node: BlockchainRpcNode) => Promise<void>;
  /** Reconnects one node, or every node when given no identifier. */
  reConnect: (identifier?: number) => Promise<void>;
  /** Whether a reconnect is in flight. */
  reconnecting: Readonly<Ref<boolean>>;
  /**
   * Asks for confirmation before removing a node.
   *
   * @remarks
   * Removing a node is not undoable, so nothing is deleted until the dialog is confirmed.
   */
  showDeleteConfirmation: (item: BlockchainRpcNode) => void;
}

/**
 * Drives the per-chain RPC node table: reading the nodes, their connectivity, and the add, edit,
 * activate, reconnect and delete actions on them.
 *
 * @param chain - the chain whose nodes are managed
 * @returns the table state and every action its rows offer
 */
export function useBlockchainRpcNodeManager(chain: MaybeRefOrGetter<Blockchain>): UseBlockchainRpcNodeManagerReturn {
  const nodes = ref<BlockchainRpcNodeList>([]);
  const modelState = ref<BlockchainRpcNodeManageState>();
  const reconnecting = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationDispatcher();
  const { setMessage } = useMessageStore();
  const { connectedNodes, coolingDownNodes, failedToConnect } = storeToRefs(useSessionMetadataStore());
  const { useChainName } = useSupportedChains();
  const api = useEvmNodesApi(() => toValue(chain));

  const chainName = useChainName(() => toValue(chain));

  function isEtherscan(item: BlockchainRpcNode): boolean {
    return !item.endpoint && item.name.includes('etherscan');
  }

  function isNodeInDataset(dataset: Record<string, string[]>, item: BlockchainRpcNode): boolean {
    const blockchain = camelCase(toValue(chain));
    const nodes = dataset?.[blockchain] || [];
    return nodes.includes(item.name);
  }

  function isNodeConnected(item: BlockchainRpcNode): boolean {
    return isEtherscan(item) || isNodeInDataset(get(connectedNodes), item);
  }

  function getNodeStatus(item: BlockchainRpcNode): NodeStatus {
    if (isNodeInDataset(get(coolingDownNodes), item))
      return NODE_STATUS.COOLING_DOWN;

    if (isNodeConnected(item))
      return NODE_STATUS.CONNECTED;

    if (isNodeInDataset(get(failedToConnect), item))
      return NODE_STATUS.FAILED;

    return NODE_STATUS.READY;
  }

  const anyDisconnected = computed<boolean>(() => get(nodes).some(node => !isNodeConnected(node) && node.active));

  async function loadNodes(): Promise<void> {
    try {
      set(nodes, await api.fetchEvmNodes());
    }
    catch (error: unknown) {
      notify({
        message: getErrorMessage(error),
        title: t('evm_rpc_node_manager.loading_error.title', {
          chain: toValue(chain),
        }),
      });
    }
  }

  function editRpcNode(node: BlockchainRpcNode): void {
    set(modelState, {
      mode: 'edit',
      node,
    });
  }

  function addNewRpcNode(): void {
    set(modelState, {
      mode: 'add',
      node: getPlaceholderNode(toValue(chain)),
    });
  }

  const { showDeleteConfirmation } = useTableRowDeletion<BlockchainRpcNode>({
    confirm: (item) => {
      const chainProp = get(chainName);
      return {
        message: t('evm_rpc_node_manager.confirm.message', {
          chain: chainProp,
          endpoint: item.endpoint,
          node: item.name,
        }),
        title: t('evm_rpc_node_manager.confirm.title', { chain: chainProp }),
      };
    },
    deleteItem: async node => api.deleteEvmNode(node.identifier),
    errorMessage: (_node, error) => ({
      description: getErrorMessage(error),
      success: false,
      title: t('evm_rpc_node_manager.delete_error.title', {
        chain: toValue(chain),
      }),
    }),
    onDeleted: loadNodes,
  });

  async function onActiveChange(active: boolean, node: BlockchainRpcNode): Promise<void> {
    try {
      await api.editEvmNode({ ...node, active });
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

  function notifyConnectFailures(messages: string[]): void {
    notify({
      message: messages.join('\n'),
      title: t('evm_rpc_node_manager.connect_error.title', { chain: get(chainName) }),
    });
  }

  async function reConnect(identifier?: number): Promise<void> {
    set(reconnecting, true);
    try {
      const { errors } = await api.reConnectNode(identifier);
      if (errors.length > 0)
        notifyConnectFailures(errors.map(({ error, name }) => `${name}: ${error}`));

      await loadNodes();
    }
    catch (error: unknown) {
      notifyConnectFailures([getErrorMessage(error)]);
    }
    finally {
      set(reconnecting, false);
    }
  }

  return {
    addNewRpcNode,
    anyDisconnected,
    editRpcNode,
    getNodeStatus,
    isEtherscan,
    loadNodes,
    modelState,
    nodes: shallowReadonly(nodes),
    onActiveChange,
    reConnect,
    reconnecting: readonly(reconnecting),
    showDeleteConfirmation,
  };
}
