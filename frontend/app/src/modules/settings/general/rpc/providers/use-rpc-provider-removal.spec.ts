import type { RpcProviderUsage } from '@/modules/settings/general/rpc/providers/rpc-provider-usage';
import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRpcProviderRemoval } from '@/modules/settings/general/rpc/providers/use-rpc-provider-removal';

const { chainsGivenToApi, deleteEvmNode, fetchEvmNodes } = vi.hoisted(() => ({
  chainsGivenToApi: vi.fn(),
  deleteEvmNode: vi.fn(),
  fetchEvmNodes: vi.fn(),
}));

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (chain: string): Record<string, unknown> => {
    chainsGivenToApi(chain);
    return { deleteEvmNode, fetchEvmNodes };
  },
}));

function node(identifier: number, endpoint: string): BlockchainRpcNode {
  return {
    active: true,
    blockchain: Blockchain.ETH,
    endpoint,
    identifier,
    name: 'Infura',
    owned: true,
    weight: 0,
  };
}

describe('settings/general/rpc/providers/use-rpc-provider-removal', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    deleteEvmNode.mockResolvedValue(true);
  });

  describe('refresh', () => {
    it('should list the providers holding nodes across the chains', async () => {
      fetchEvmNodes
        .mockResolvedValueOnce([node(1, 'https://mainnet.infura.io/v3/key')])
        .mockResolvedValueOnce([node(2, 'https://optimism-mainnet.infura.io/v3/key')]);

      const { refresh, usages } = useRpcProviderRemoval();
      await refresh([Blockchain.ETH, Blockchain.OPTIMISM]);

      expect(get(usages)).toHaveLength(1);
      expect(get(usages)[0].nodes).toHaveLength(2);
    });

    it('should hold nothing when no provider node is found', async () => {
      fetchEvmNodes.mockResolvedValue([node(1, 'https://eth-rpc.publicnode.com')]);

      const { refresh, usages } = useRpcProviderRemoval();
      await refresh([Blockchain.ETH]);

      expect(get(usages)).toEqual([]);
    });
  });

  describe('removeAll', () => {
    const usage: RpcProviderUsage = {
      id: 'infura',
      key: '0123…cdef',
      name: 'Infura',
      nodes: [
        { chain: Blockchain.ETH, identifier: 1, name: 'Infura' },
        { chain: Blockchain.OPTIMISM, identifier: 2, name: 'Infura' },
      ],
    };

    it('should delete every node of the provider, on its own chain', async () => {
      const { removeAll } = useRpcProviderRemoval();

      expect(await removeAll(usage)).toEqual({ failed: 0, removed: 2 });
      expect(deleteEvmNode).toHaveBeenCalledWith(1);
      expect(deleteEvmNode).toHaveBeenCalledWith(2);
      expect(chainsGivenToApi).toHaveBeenCalledWith(Blockchain.OPTIMISM);
    });

    it('should keep going when one chain refuses, and count it', async () => {
      deleteEvmNode.mockRejectedValueOnce(new Error('nope')).mockResolvedValueOnce(true);

      const { removeAll } = useRpcProviderRemoval();

      expect(await removeAll(usage)).toEqual({ failed: 1, removed: 1 });
      expect(deleteEvmNode).toHaveBeenCalledTimes(2);
    });

    it('should hold the in-flight flag for the whole removal', async () => {
      const { removeAll, removing } = useRpcProviderRemoval();
      const pending = removeAll(usage);

      expect(get(removing)).toBe(true);
      await pending;
      expect(get(removing)).toBe(false);
    });
  });
});
