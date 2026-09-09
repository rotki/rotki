import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { NODE_STATUS } from '@/modules/settings/general/rpc/rpc-node-status';
import { useBlockchainRpcNodeManager } from './use-blockchain-rpc-node-manager';

let connectedNodes: Ref<Record<string, string[]>>;
let coolingDownNodes: Ref<Record<string, string[]>>;
let failedToConnect: Ref<Record<string, string[]>>;
let scope: ReturnType<typeof effectScope>;

const {
  chainGivenToApi,
  chainGivenToChainName,
  deleteEvmNode,
  editEvmNode,
  fetchEvmNodes,
  notify,
  reConnectNode,
  setMessage,
} = vi.hoisted(() => ({
  chainGivenToApi: vi.fn(),
  chainGivenToChainName: vi.fn(),
  deleteEvmNode: vi.fn(async () => Promise.resolve(true)),
  editEvmNode: vi.fn(async () => Promise.resolve(true)),
  fetchEvmNodes: vi.fn(),
  notify: vi.fn(),
  reConnectNode: vi.fn(async (): Promise<{ errors: { error: string; name: string }[] }> => ({ errors: [] })),
  setMessage: vi.fn(),
}));

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (chain: () => string): Record<string, unknown> => {
    chainGivenToApi(chain());
    return {
      deleteEvmNode,
      editEvmNode,
      fetchEvmNodes,
      reConnectNode,
    };
  },
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    useChainName: (chain: () => string): Ref<string> => {
      chainGivenToChainName(chain());
      return ref('Ethereum');
    },
  }),
}));

vi.mock('@/modules/session/use-session-metadata-store', () => ({
  useSessionMetadataStore: (): Record<string, unknown> => ({
    connectedNodes,
    coolingDownNodes,
    failedToConnect,
  }),
}));

function node(overrides: Partial<BlockchainRpcNode> = {}): BlockchainRpcNode {
  return {
    active: true,
    blockchain: 'eth',
    endpoint: 'https://example.com',
    identifier: 1,
    name: 'my node',
    owned: true,
    weight: 50,
    ...overrides,
  };
}

function manager(): ReturnType<typeof useBlockchainRpcNodeManager> {
  scope = effectScope();
  return scope.run(() => useBlockchainRpcNodeManager(Blockchain.ETH))!;
}

describe('modules/settings/general/rpc/useBlockchainRpcNodeManager', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    connectedNodes = ref<Record<string, string[]>>({});
    coolingDownNodes = ref<Record<string, string[]>>({});
    failedToConnect = ref<Record<string, string[]>>({});
    fetchEvmNodes.mockResolvedValue([]);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('reading the nodes', () => {
    it('should scope the api and the chain name to the chain it was given', () => {
      manager();

      expect(chainGivenToApi).toHaveBeenCalledWith('eth');
      expect(chainGivenToChainName).toHaveBeenCalledWith('eth');
    });

    it('should read them for the chain it manages', async () => {
      fetchEvmNodes.mockResolvedValue([node({ name: 'first' })]);

      const { loadNodes, nodes } = manager();
      await loadNodes();

      expect(get(nodes)).toHaveLength(1);
      expect(get(nodes)[0].name).toBe('first');
    });

    it('should report a failure as a notification rather than a message', async () => {
      fetchEvmNodes.mockRejectedValue(new Error('backend is down'));

      const { loadNodes, nodes } = manager();
      await loadNodes();

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'backend is down' }));
      expect(setMessage).not.toHaveBeenCalled();
      expect(get(nodes)).toHaveLength(0);
    });
  });

  describe('the etherscan entry', () => {
    it('should recognise it by having no endpoint', () => {
      const { isEtherscan } = manager();

      expect(isEtherscan(node({ endpoint: '', name: 'etherscan' }))).toBe(true);
    });

    it.each([
      ['it has an endpoint', node({ endpoint: 'https://example.com', name: 'etherscan' })],
      ['it is not named etherscan', node({ endpoint: '', name: 'my node' })],
    ])('should not recognise a node when %s', (_case, item) => {
      const { isEtherscan } = manager();

      expect(isEtherscan(item)).toBe(false);
    });

    it('should treat it as connected without it appearing in the connected set', () => {
      const { getNodeStatus } = manager();

      expect(getNodeStatus(node({ endpoint: '', name: 'etherscan' }))).toBe(NODE_STATUS.CONNECTED);
    });
  });

  describe('connectivity', () => {
    it('should read the chain key in camel case', () => {
      set(connectedNodes, { eth: ['my node'] });

      const { getNodeStatus } = manager();

      expect(getNodeStatus(node())).toBe(NODE_STATUS.CONNECTED);
    });

    it('should rank cooling down above connected', () => {
      set(connectedNodes, { eth: ['my node'] });
      set(coolingDownNodes, { eth: ['my node'] });

      const { getNodeStatus } = manager();

      expect(getNodeStatus(node())).toBe(NODE_STATUS.COOLING_DOWN);
    });

    it('should report a node that failed to connect', () => {
      set(failedToConnect, { eth: ['my node'] });

      const { getNodeStatus } = manager();

      expect(getNodeStatus(node())).toBe(NODE_STATUS.FAILED);
    });

    it('should report a node no set mentions as ready', () => {
      const { getNodeStatus } = manager();

      expect(getNodeStatus(node())).toBe(NODE_STATUS.READY);
    });

    it('should offer reconnect-all while an active node is disconnected', async () => {
      fetchEvmNodes.mockResolvedValue([node({ active: true })]);

      const { anyDisconnected, loadNodes } = manager();
      await loadNodes();

      expect(get(anyDisconnected)).toBe(true);
    });

    it('should not offer reconnect-all for a disconnected node that is switched off', async () => {
      fetchEvmNodes.mockResolvedValue([node({ active: false })]);

      const { anyDisconnected, loadNodes } = manager();
      await loadNodes();

      expect(get(anyDisconnected)).toBe(false);
    });
  });

  describe('the add and edit form', () => {
    it('should open a blank node for this chain to add', () => {
      const { addNewRpcNode, modelState } = manager();
      addNewRpcNode();

      expect(get(modelState)).toEqual({
        mode: 'add',
        node: expect.objectContaining({ blockchain: 'eth', identifier: -1, name: '' }),
      });
    });

    it('should open an existing node to edit', () => {
      const existing = node({ identifier: 9 });

      const { editRpcNode, modelState } = manager();
      editRpcNode(existing);

      expect(get(modelState)).toEqual({ mode: 'edit', node: existing });
    });
  });

  describe('activating a node', () => {
    it('should send the node with its new active flag and re-read the list', async () => {
      const { onActiveChange } = manager();
      await onActiveChange(false, node({ identifier: 4 }));

      expect(editEvmNode).toHaveBeenCalledWith(expect.objectContaining({ active: false, identifier: 4 }));
      expect(fetchEvmNodes).toHaveBeenCalledOnce();
    });

    it('should report a failure and not re-read the list', async () => {
      editEvmNode.mockRejectedValue(new Error('rejected'));

      const { onActiveChange } = manager();
      await onActiveChange(false, node({ name: 'my node' }));

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
      expect(fetchEvmNodes).not.toHaveBeenCalled();
    });
  });

  describe('deleting a node', () => {
    it('should delete nothing until the dialog is confirmed', () => {
      const { showDeleteConfirmation } = manager();
      showDeleteConfirmation(node({ identifier: 3 }));

      expect(get(useConfirmStore().visible)).toBe(true);
      expect(deleteEvmNode).not.toHaveBeenCalled();
    });

    it('should delete exactly the node the dialog named', async () => {
      const { showDeleteConfirmation } = manager();
      showDeleteConfirmation(node({ identifier: 3 }));
      await useConfirmStore().confirm();
      await flushPromises();

      expect(deleteEvmNode).toHaveBeenCalledWith(3);
      expect(deleteEvmNode).toHaveBeenCalledOnce();
      expect(fetchEvmNodes).toHaveBeenCalledOnce();
    });

    it('should delete nothing when the dialog is dismissed', async () => {
      const { showDeleteConfirmation } = manager();
      showDeleteConfirmation(node({ identifier: 3 }));
      await useConfirmStore().dismiss();
      await flushPromises();

      expect(deleteEvmNode).not.toHaveBeenCalled();
    });

    it('should report a failure and not re-read the list', async () => {
      deleteEvmNode.mockRejectedValue(new Error('still in use'));

      const { showDeleteConfirmation } = manager();
      showDeleteConfirmation(node({ identifier: 3 }));
      await useConfirmStore().confirm();
      await flushPromises();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
      expect(fetchEvmNodes).not.toHaveBeenCalled();
    });
  });

  describe('reconnecting', () => {
    it('should reconnect one node and re-read the list', async () => {
      const { reConnect, reconnecting } = manager();
      const pending = reConnect(6);
      expect(get(reconnecting)).toBe(true);

      await pending;

      expect(reConnectNode).toHaveBeenCalledWith(6);
      expect(get(reconnecting)).toBe(false);
      expect(fetchEvmNodes).toHaveBeenCalledOnce();
    });

    it('should reconnect every node when given no identifier', async () => {
      const { reConnect } = manager();
      await reConnect();

      expect(reConnectNode).toHaveBeenCalledWith(undefined);
    });

    it('should notify with the nodes that failed, and still re-read the list', async () => {
      reConnectNode.mockResolvedValue({ errors: [{ error: 'refused', name: 'my node' }] });

      const { reConnect, reconnecting } = manager();
      await reConnect(6);

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'my node: refused' }));
      expect(fetchEvmNodes).toHaveBeenCalledOnce();
      expect(get(reconnecting)).toBe(false);
    });

    it('should notify and clear the in-flight flag when the reconnect throws', async () => {
      reConnectNode.mockRejectedValue(new Error('offline'));

      const { reConnect, reconnecting } = manager();
      await reConnect(6);

      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ message: 'offline' }));
      expect(get(reconnecting)).toBe(false);
    });
  });
});
