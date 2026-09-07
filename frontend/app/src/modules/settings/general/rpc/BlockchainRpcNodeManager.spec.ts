import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import BlockchainRpcNodeManager from '@/modules/settings/general/rpc/BlockchainRpcNodeManager.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

let connectedNodes: Ref<Record<string, string[]>>;
let coolingDownNodes: Ref<Record<string, string[]>>;
let failedToConnect: Ref<Record<string, string[]>>;

const { deleteEvmNode, editEvmNode, fetchEvmNodes, reConnectNode } = vi.hoisted(() => ({
  deleteEvmNode: vi.fn(async () => Promise.resolve(true)),
  editEvmNode: vi.fn(async () => Promise.resolve(true)),
  fetchEvmNodes: vi.fn(),
  reConnectNode: vi.fn(async () => Promise.resolve(true)),
}));

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (): Record<string, unknown> => ({
    deleteEvmNode,
    editEvmNode,
    fetchEvmNodes,
    reConnectNode,
  }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify: vi.fn() }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    useChainName: (): Ref<string> => ref('Ethereum'),
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

async function createWrapper(nodes: BlockchainRpcNode[]): Promise<VueWrapper> {
  fetchEvmNodes.mockResolvedValue(nodes);
  const wrapper = mount(BlockchainRpcNodeManager, {
    global: {
      plugins: [createCustomPinia()],
      stubs: { BlockchainRpcNodeFormDialog: true, RpcNodeStatusCell: true, RpcReconnectButton: true },
    },
    props: { chain: Blockchain.ETH },
  });
  await flushPromises();
  return wrapper;
}

describe('modules/settings/general/rpc/BlockchainRpcNodeManager.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    connectedNodes = ref<Record<string, string[]>>({});
    coolingDownNodes = ref<Record<string, string[]>>({});
    failedToConnect = ref<Record<string, string[]>>({});
  });

  it('should read the nodes when it opens', async () => {
    await createWrapper([]);

    expect(fetchEvmNodes).toHaveBeenCalledOnce();
  });

  it('should render one row per node', async () => {
    const wrapper = await createWrapper([node({ identifier: 1, name: 'first' }), node({ identifier: 2, name: 'second' })]);

    expect(wrapper.findAll('[data-testid=ethereum-node]')).toHaveLength(2);
  });

  it('should show the etherscan label in place of an endpoint', async () => {
    const wrapper = await createWrapper([node({ endpoint: '', name: 'etherscan' })]);

    expect(wrapper.text()).toContain('evm_rpc_node_manager.etherscan');
  });

  it('should not let the etherscan entry be deleted or switched off', async () => {
    const wrapper = await createWrapper([node({ endpoint: '', name: 'etherscan' })]);

    expect(wrapper.findComponent(RowActions).props('deleteDisabled')).toBe(true);
    expect(wrapper.find('[data-testid=node-active] input').attributes('disabled')).toBeDefined();
  });

  it('should let an ordinary node be deleted', async () => {
    const wrapper = await createWrapper([node()]);

    expect(wrapper.findComponent(RowActions).props('deleteDisabled')).toBe(false);
  });

  it('should ask before deleting, and delete nothing until confirmed', async () => {
    const wrapper = await createWrapper([node({ identifier: 8 })]);

    wrapper.findComponent(RowActions).vm.$emit('delete-click');
    await flushPromises();

    expect(get(useConfirmStore().visible)).toBe(true);
    expect(deleteEvmNode).not.toHaveBeenCalled();
  });

  it('should offer reconnect-all only while an active node is disconnected', async () => {
    const disconnected = await createWrapper([node({ active: true })]);
    expect(disconnected.find('[data-testid=reconnect-all]').exists()).toBe(true);

    set(connectedNodes, { eth: ['my node'] });
    const connected = await createWrapper([node({ active: true })]);
    expect(connected.find('[data-testid=reconnect-all]').exists()).toBe(false);
  });

  it('should send the node when its switch is toggled', async () => {
    const wrapper = await createWrapper([node({ identifier: 4 })]);

    await wrapper.find('[data-testid=node-active] input').setValue(false);
    await flushPromises();

    expect(editEvmNode).toHaveBeenCalledWith(expect.objectContaining({ active: false, identifier: 4 }));
  });
});
