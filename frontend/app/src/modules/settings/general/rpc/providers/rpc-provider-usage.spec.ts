import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { groupNodesByProvider } from '@/modules/settings/general/rpc/providers/rpc-provider-usage';

function node(identifier: number, endpoint: string, name = 'a node'): BlockchainRpcNode {
  return {
    active: true,
    blockchain: Blockchain.ETH,
    endpoint,
    identifier,
    name,
    owned: true,
    weight: 0,
  };
}

describe('settings/general/rpc/providers/rpc-provider-usage', () => {
  it('should gather one provider\'s nodes from every chain', () => {
    const usages = groupNodesByProvider({
      [Blockchain.ETH]: [node(1, 'https://mainnet.infura.io/v3/key', 'Infura')],
      [Blockchain.OPTIMISM]: [node(2, 'https://optimism-mainnet.infura.io/v3/key', 'Infura')],
    });

    expect(usages).toHaveLength(1);
    expect(usages[0]).toMatchObject({ id: 'infura', name: 'Infura' });
    expect(usages[0].nodes).toEqual([
      { chain: Blockchain.ETH, identifier: 1, name: 'Infura' },
      { chain: Blockchain.OPTIMISM, identifier: 2, name: 'Infura' },
    ]);
  });

  it('should keep providers apart and leave everything else alone', () => {
    const usages = groupNodesByProvider({
      [Blockchain.ETH]: [
        node(1, 'https://mainnet.infura.io/v3/key'),
        node(2, 'https://eth-mainnet.g.alchemy.com/v2/key'),
        node(3, 'https://eth-rpc.publicnode.com'),
        node(4, '', 'etherscan'),
      ],
    });

    expect(usages.map(usage => usage.id)).toEqual(['infura', 'alchemy']);
    expect(usages.every(usage => usage.nodes.length === 1)).toBe(true);
  });

  it('should keep two keys of one provider apart, so removing one leaves the other', () => {
    const usages = groupNodesByProvider({
      [Blockchain.ETH]: [
        node(1, 'https://mainnet.infura.io/v3/0123456789abcdef', 'Personal'),
        node(2, 'https://mainnet.infura.io/v3/fedcba9876543210', 'Work'),
      ],
      [Blockchain.OPTIMISM]: [node(3, 'https://optimism-mainnet.infura.io/v3/fedcba9876543210', 'Work')],
    });

    expect(usages).toHaveLength(2);
    expect(usages.map(usage => usage.nodes.map(entry => entry.identifier))).toEqual([[1], [2, 3]]);
    expect(new Set(usages.map(usage => usage.key)).size).toBe(2);
  });

  it('should mask the key it groups by, so the raw credential never leaves the module', () => {
    const usages = groupNodesByProvider({
      [Blockchain.ETH]: [node(1, 'https://mainnet.infura.io/v3/0123456789abcdef')],
    });

    expect(usages[0].key).toBe('0123…cdef');
    expect(JSON.stringify(usages)).not.toContain('0123456789abcdef');
  });

  it('should keep the same quicknode token on two endpoint names apart', () => {
    const usages = groupNodesByProvider({
      [Blockchain.OPTIMISM]: [
        node(1, 'https://vineyard.optimism.quiknode.pro/token/'),
        node(2, 'https://orchard.optimism.quiknode.pro/token/'),
      ],
    });

    expect(usages).toHaveLength(2);
  });

  it('should bucket a provider url it cannot parse rather than dropping it', () => {
    const usages = groupNodesByProvider({
      [Blockchain.ETH]: [node(1, 'https://mainnet.infura.io/v3/key/extra/segments', 'hand written')],
    });

    expect(usages).toHaveLength(1);
    expect(usages[0]).toMatchObject({ id: 'infura', key: '' });
  });

  it('should group a node added by hand, since nothing records where a node came from', () => {
    const usages = groupNodesByProvider({
      [Blockchain.ETH]: [node(9, 'https://mainnet.infura.io/v3/some-other-key', 'my own node')],
    });

    expect(usages[0].nodes).toEqual([{ chain: Blockchain.ETH, identifier: 9, name: 'my own node' }]);
  });

  it('should return nothing when no provider holds a node', () => {
    expect(groupNodesByProvider({ [Blockchain.ETH]: [node(1, 'https://eth-rpc.publicnode.com')] })).toEqual([]);
    expect(groupNodesByProvider({})).toEqual([]);
  });
});
