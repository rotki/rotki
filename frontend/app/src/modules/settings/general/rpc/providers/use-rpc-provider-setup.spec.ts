import type { RpcProviderCandidate } from '@/modules/settings/general/rpc/providers/rpc-provider-plan';
import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  RPC_SETUP_STATUS,
  useRpcProviderSetup,
} from '@/modules/settings/general/rpc/providers/use-rpc-provider-setup';

const { addEvmNode, chainsGivenToApi, deleteEvmNode, editEvmNode, fetchEvmNodes, reConnectNode } = vi.hoisted(() => ({
  addEvmNode: vi.fn(),
  chainsGivenToApi: vi.fn(),
  deleteEvmNode: vi.fn(),
  editEvmNode: vi.fn(),
  fetchEvmNodes: vi.fn(),
  reConnectNode: vi.fn(),
}));

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (chain: string): Record<string, unknown> => {
    chainsGivenToApi(chain);
    return { addEvmNode, deleteEvmNode, editEvmNode, fetchEvmNodes, reConnectNode };
  },
}));

function node(partial: Partial<BlockchainRpcNode>): BlockchainRpcNode {
  return {
    active: true,
    blockchain: Blockchain.ETH,
    endpoint: 'https://mainnet.infura.io/v3/abcdef',
    identifier: 7,
    name: 'Infura',
    owned: true,
    weight: 0,
    ...partial,
  };
}

function candidate(partial: Partial<RpcProviderCandidate> = {}): RpcProviderCandidate {
  return {
    chain: Blockchain.ETH,
    endpoint: 'https://mainnet.infura.io/v3/abcdef',
    name: 'Infura',
    ...partial,
  };
}

describe('settings/general/rpc/providers/use-rpc-provider-setup', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    addEvmNode.mockResolvedValue(true);
    deleteEvmNode.mockResolvedValue(true);
    editEvmNode.mockResolvedValue(true);
    reConnectNode.mockResolvedValue({ errors: [] });
    fetchEvmNodes.mockResolvedValue([node({})]);
  });

  describe('run', () => {
    it('should add, connect and keep a node that answers', async () => {
      fetchEvmNodes.mockResolvedValue([node({ isArchive: true })]);

      const { rows, run, summary } = useRpcProviderSetup();
      await run([candidate()]);

      expect(addEvmNode).toHaveBeenCalledWith({
        active: true,
        blockchain: Blockchain.ETH,
        endpoint: 'https://mainnet.infura.io/v3/abcdef',
        name: 'Infura',
        owned: true,
        weight: 0,
      });
      expect(reConnectNode).toHaveBeenCalledWith(7);
      expect(deleteEvmNode).not.toHaveBeenCalled();
      expect(get(rows)[0]).toMatchObject({ archive: true, status: RPC_SETUP_STATUS.ADDED });
      expect(get(summary)).toEqual({ added: 1, archive: 1, failed: 0, total: 1 });
    });

    it('should mark a connected node without archive support', async () => {
      fetchEvmNodes.mockResolvedValue([node({ isArchive: false })]);

      const { rows, summary, run } = useRpcProviderSetup();
      await run([candidate()]);

      expect(get(rows)[0]).toMatchObject({ archive: false, status: RPC_SETUP_STATUS.ADDED });
      expect(get(summary).archive).toBe(0);
    });

    it('should delete the node again when the connect reports an error', async () => {
      reConnectNode.mockResolvedValue({ errors: [{ error: 'not enabled for this key', name: 'Infura' }] });

      const { rows, summary, run } = useRpcProviderSetup();
      await run([candidate()]);

      expect(deleteEvmNode).toHaveBeenCalledWith(7);
      expect(get(rows)[0]).toMatchObject({
        error: 'not enabled for this key',
        status: RPC_SETUP_STATUS.FAILED,
      });
      expect(get(summary)).toEqual({ added: 0, archive: 0, failed: 1, total: 1 });
    });

    it('should delete the node again when the connect itself throws', async () => {
      reConnectNode.mockRejectedValue(new Error('backend is gone'));

      const { rows, run } = useRpcProviderSetup();
      await run([candidate()]);

      expect(deleteEvmNode).toHaveBeenCalledWith(7);
      expect(get(rows)[0]).toMatchObject({ error: 'backend is gone', status: RPC_SETUP_STATUS.FAILED });
    });

    it('should not connect or delete anything when the add fails', async () => {
      addEvmNode.mockRejectedValue(new Error('the backend is gone'));
      fetchEvmNodes.mockResolvedValue([]);

      const { rows, run } = useRpcProviderSetup();
      await run([candidate()]);

      expect(reConnectNode).not.toHaveBeenCalled();
      expect(deleteEvmNode).not.toHaveBeenCalled();
      expect(get(rows)[0]).toMatchObject({ error: 'the backend is gone', status: RPC_SETUP_STATUS.FAILED });
    });

    it('should adopt a node an earlier attempt left behind rather than fail on the duplicate', async () => {
      addEvmNode.mockRejectedValue(new Error('already exists in db'));

      const { rows, run } = useRpcProviderSetup();
      await run([candidate()]);

      expect(reConnectNode).toHaveBeenCalledWith(7);
      expect(get(rows)[0].status).toBe(RPC_SETUP_STATUS.ADDED);
    });

    it('should update the endpoint of a node holding an older key instead of adding a second one', async () => {
      const older = node({ endpoint: 'https://mainnet.infura.io/v3/older', name: 'Infura', weight: 25 });

      const { rows, run } = useRpcProviderSetup();
      await run([candidate({ outdated: older })]);

      expect(addEvmNode).not.toHaveBeenCalled();
      expect(editEvmNode).toHaveBeenCalledWith({ ...older, endpoint: 'https://mainnet.infura.io/v3/abcdef' });
      expect(get(rows)[0].status).toBe(RPC_SETUP_STATUS.UPDATED);
    });

    it('should put the older key back when the updated endpoint cannot connect', async () => {
      const older = node({ endpoint: 'https://mainnet.infura.io/v3/older', name: 'Infura', weight: 25 });
      reConnectNode.mockResolvedValue({ errors: [{ error: 'nope', name: 'Infura' }] });

      const { rows, run } = useRpcProviderSetup();
      await run([candidate({ outdated: older })]);

      expect(editEvmNode).toHaveBeenLastCalledWith(older);
      expect(deleteEvmNode).not.toHaveBeenCalled();
      expect(get(rows)[0].status).toBe(RPC_SETUP_STATUS.FAILED);
    });

    it('should fail the row when the added node cannot be found again', async () => {
      fetchEvmNodes.mockResolvedValue([node({ endpoint: 'https://something.else' })]);

      const { rows, run } = useRpcProviderSetup();
      await run([candidate()]);

      expect(reConnectNode).not.toHaveBeenCalled();
      expect(get(rows)[0].status).toBe(RPC_SETUP_STATUS.FAILED);
    });

    it('should keep going after a failure and report each chain on its own', async () => {
      fetchEvmNodes.mockImplementation(async () => [node({})]);
      reConnectNode
        .mockResolvedValueOnce({ errors: [{ error: 'nope', name: 'Infura' }] })
        .mockResolvedValueOnce({ errors: [] });

      const { rows, summary, run } = useRpcProviderSetup();
      await run([candidate(), candidate({ chain: Blockchain.OPTIMISM })]);

      expect(get(rows).map(row => row.status)).toEqual([RPC_SETUP_STATUS.FAILED, RPC_SETUP_STATUS.ADDED]);
      expect(get(summary)).toEqual({ added: 1, archive: 0, failed: 1, total: 2 });
      expect(chainsGivenToApi).toHaveBeenCalledWith(Blockchain.OPTIMISM);
    });

    it('should walk the chains one at a time', async () => {
      const order: string[] = [];
      addEvmNode.mockImplementation(async () => {
        order.push('add');
        return true;
      });
      reConnectNode.mockImplementation(async () => {
        order.push('connect');
        return { errors: [] };
      });

      const { run } = useRpcProviderSetup();
      await run([candidate(), candidate({ chain: Blockchain.OPTIMISM })]);

      expect(order).toEqual(['add', 'connect', 'add', 'connect']);
    });

    it('should hold the in-flight flag for the whole run and clear it at the end', async () => {
      const { run, running } = useRpcProviderSetup();
      const pending = run([candidate()]);

      expect(get(running)).toBe(true);
      await pending;
      expect(get(running)).toBe(false);
    });

    it('should start every row as pending', async () => {
      const { rows, run } = useRpcProviderSetup();
      const pending = run([candidate(), candidate({ chain: Blockchain.OPTIMISM })]);

      expect(get(rows).map(row => row.status)).toEqual([RPC_SETUP_STATUS.RUNNING, RPC_SETUP_STATUS.PENDING]);
      await pending;
    });
  });

  describe('retry', () => {
    it('should keep the rows of the chains it is not retrying', async () => {
      reConnectNode
        .mockResolvedValueOnce({ errors: [] })
        .mockResolvedValueOnce({ errors: [{ error: 'nope', name: 'Infura' }] });

      const { retry, rows, run, summary } = useRpcProviderSetup();
      await run([candidate(), candidate({ chain: Blockchain.OPTIMISM })]);
      expect(get(summary)).toEqual({ added: 1, archive: 0, failed: 1, total: 2 });

      reConnectNode.mockResolvedValue({ errors: [] });
      await retry([candidate({ chain: Blockchain.OPTIMISM })]);

      expect(get(rows).map(row => row.status)).toEqual([RPC_SETUP_STATUS.ADDED, RPC_SETUP_STATUS.ADDED]);
      expect(get(summary)).toEqual({ added: 2, archive: 0, failed: 0, total: 2 });
    });
  });

  describe('stop', () => {
    it('should leave the chains behind the one it is on untouched', async () => {
      const { rows, run, stop } = useRpcProviderSetup();
      addEvmNode.mockImplementation(async () => {
        stop();
        return true;
      });

      await run([candidate(), candidate({ chain: Blockchain.OPTIMISM })]);

      expect(addEvmNode).toHaveBeenCalledOnce();
      expect(get(rows)[1].status).toBe(RPC_SETUP_STATUS.PENDING);
    });

    it('should clear the in-flight flag it abandons', async () => {
      const { run, running, stop } = useRpcProviderSetup();
      addEvmNode.mockImplementation(async () => {
        stop();
        return true;
      });

      await run([candidate()]);

      expect(get(running)).toBe(false);
    });

    it('should not carry a stop into the next run', async () => {
      const { run, stop } = useRpcProviderSetup();
      stop();

      await run([candidate(), candidate({ chain: Blockchain.OPTIMISM })]);

      expect(addEvmNode).toHaveBeenCalledTimes(2);
    });

    it('should drop the writes of an abandoned run that is still in flight', async () => {
      const { rows, run, stop } = useRpcProviderSetup();
      let releaseAbandoned = (): void => {};
      const abandonedConnect = new Promise<{ errors: { error: string; name: string }[] }>((resolve) => {
        releaseAbandoned = (): void => resolve({ errors: [{ error: 'from the abandoned run', name: 'Infura' }] });
      });
      reConnectNode.mockReturnValueOnce(abandonedConnect).mockResolvedValue({ errors: [] });

      const abandoned = run([candidate()]);
      await flushPromises();
      stop();

      await run([candidate()]);
      expect(get(rows)[0].status).toBe(RPC_SETUP_STATUS.ADDED);

      releaseAbandoned();
      await abandoned;

      expect(get(rows)[0]).toMatchObject({ chain: Blockchain.ETH, status: RPC_SETUP_STATUS.ADDED });
    });
  });

  describe('loadExisting', () => {
    it('should read the nodes of every chain', async () => {
      const eth = node({});
      const optimism = node({ blockchain: Blockchain.OPTIMISM, identifier: 8 });
      fetchEvmNodes.mockResolvedValueOnce([eth]).mockResolvedValueOnce([optimism]);

      const { loadExisting } = useRpcProviderSetup();

      expect(await loadExisting([Blockchain.ETH, Blockchain.OPTIMISM])).toEqual({
        nodes: {
          [Blockchain.ETH]: [eth],
          [Blockchain.OPTIMISM]: [optimism],
        },
        unreadable: [],
      });
    });

    it('should name a chain whose nodes cannot be read rather than call it empty', async () => {
      fetchEvmNodes.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce([node({})]);

      const { loadExisting } = useRpcProviderSetup();
      const existing = await loadExisting([Blockchain.ETH, Blockchain.OPTIMISM]);

      expect(existing.unreadable).toEqual([Blockchain.ETH]);
      expect(existing.nodes[Blockchain.ETH]).toBeUndefined();
      expect(existing.nodes[Blockchain.OPTIMISM]).toHaveLength(1);
    });
  });

  describe('reset', () => {
    it('should drop the rows of a finished run', async () => {
      const { reset, rows, run } = useRpcProviderSetup();
      await run([candidate()]);
      reset();

      expect(get(rows)).toEqual([]);
    });
  });
});
