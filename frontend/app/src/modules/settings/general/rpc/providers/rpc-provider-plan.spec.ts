import type { RpcProviderMatch } from '@/modules/settings/general/rpc/providers/rpc-providers';
import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  buildRpcProviderPlan,
  toRpcNodePayload,
} from '@/modules/settings/general/rpc/providers/rpc-provider-plan';

function node(partial: Partial<BlockchainRpcNode>): BlockchainRpcNode {
  return {
    active: true,
    blockchain: Blockchain.ETH,
    endpoint: 'https://rpc.example.com',
    identifier: 1,
    name: 'a node',
    owned: false,
    weight: 20,
    ...partial,
  };
}

const infura: RpcProviderMatch = {
  chain: Blockchain.ETH,
  credentials: { key: 'abcdef' },
  providerId: 'infura',
};

describe('settings/general/rpc/providers/rpc-provider-plan', () => {
  describe('buildRpcProviderPlan', () => {
    it('should build one candidate per served chain, in the order given', () => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.OPTIMISM, Blockchain.ETH], {});

      expect(candidates.map(candidate => candidate.chain)).toEqual([Blockchain.OPTIMISM, Blockchain.ETH]);
      expect(candidates[1].endpoint).toBe('https://mainnet.infura.io/v3/abcdef');
      expect(candidates[1].name).toBe('Infura');
    });

    it('should report the chains the provider does not serve instead of dropping them', () => {
      const { candidates, unsupported } = buildRpcProviderPlan(
        infura,
        [Blockchain.ETH, Blockchain.GNOSIS, Blockchain.SONIC],
        {},
      );

      expect(candidates).toHaveLength(1);
      expect(unsupported).toEqual([Blockchain.GNOSIS, Blockchain.SONIC]);
    });

    it('should flag a chain that already holds exactly this endpoint', () => {
      const existing = node({ endpoint: 'https://mainnet.infura.io/v3/abcdef', name: 'Infura' });
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], { [Blockchain.ETH]: [existing] });

      expect(candidates[0].existing).toBe(existing);
      expect(candidates[0].outdated).toBeUndefined();
    });

    it('should offer to update a node holding the same provider with an older key', () => {
      const older = node({ endpoint: 'https://mainnet.infura.io/v3/an-older-key', name: 'Infura' });
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], { [Blockchain.ETH]: [older] });

      expect(candidates[0].existing).toBeUndefined();
      expect(candidates[0].outdated).toBe(older);
    });

    it('should ignore nodes from other providers when looking for an existing one', () => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], {
        [Blockchain.ETH]: [
          node({ endpoint: 'https://eth-mainnet.g.alchemy.com/v2/key' }),
          node({ endpoint: '', name: 'etherscan' }),
        ],
      });

      expect(candidates[0].existing).toBeUndefined();
      expect(candidates[0].outdated).toBeUndefined();
    });

    it('should not collide with an existing node of the same name', () => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], {
        [Blockchain.ETH]: [
          node({ endpoint: 'https://other.example.com', name: 'Infura' }),
          node({ endpoint: 'https://another.example.com', name: 'Infura (2)' }),
        ],
      });

      expect(candidates[0].name).toBe('Infura (3)');
    });

    it('should name the nodes what the caller asked for', () => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], {}, 'Work key');

      expect(candidates[0].name).toBe('Work key');
    });

    it('should keep a custom name unique against the names a chain already holds', () => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], {
        [Blockchain.ETH]: [node({ endpoint: 'https://other.example.com', name: 'Work key' })],
      }, 'Work key');

      expect(candidates[0].name).toBe('Work key (2)');
    });

    it.each([
      ['an empty name', ''],
      ['only whitespace', '   '],
    ])('should fall back to the provider name given %s', (_case, preferred) => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], {}, preferred);

      expect(candidates[0].name).toBe('Infura');
    });

    it('should treat a chain with no known nodes as empty', () => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.BSC], {});

      expect(candidates[0].existing).toBeUndefined();
      expect(candidates[0].name).toBe('Infura');
    });
  });

  describe('toRpcNodePayload', () => {
    it('should add the node as owned with a zero weight, so existing weights are untouched', () => {
      const { candidates } = buildRpcProviderPlan(infura, [Blockchain.ETH], {});

      expect(toRpcNodePayload(candidates[0])).toEqual({
        active: true,
        blockchain: Blockchain.ETH,
        endpoint: 'https://mainnet.infura.io/v3/abcdef',
        name: 'Infura',
        owned: true,
        weight: 0,
      });
    });
  });
});
