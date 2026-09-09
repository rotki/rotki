import { Blockchain } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  buildRpcEndpoint,
  detectRpcProvider,
  getRpcProvider,
  isRpcProviderEndpoint,
  maskRpcEndpoint,
  maskRpcKey,
  type RpcProviderMatch,
} from '@/modules/settings/general/rpc/providers/rpc-providers';

describe('settings/general/rpc/providers/rpc-providers', () => {
  describe('detectRpcProvider', () => {
    it('should detect infura with the chain the network slug names', () => {
      expect(detectRpcProvider('https://mainnet.infura.io/v3/abcdef')).toEqual({
        chain: Blockchain.ETH,
        credentials: { key: 'abcdef' },
        providerId: 'infura',
      });

      expect(detectRpcProvider('https://optimism-mainnet.infura.io/v3/abcdef')).toMatchObject({
        chain: Blockchain.OPTIMISM,
        providerId: 'infura',
      });
    });

    it('should detect alchemy', () => {
      expect(detectRpcProvider('https://eth-mainnet.g.alchemy.com/v2/key-123')).toEqual({
        chain: Blockchain.ETH,
        credentials: { key: 'key-123' },
        providerId: 'alchemy',
      });
    });

    it('should detect quicknode with its endpoint name and network subdomain', () => {
      expect(detectRpcProvider('https://hidden-vineyard.optimism.quiknode.pro/token123/')).toEqual({
        chain: Blockchain.OPTIMISM,
        credentials: { endpointName: 'hidden-vineyard', key: 'token123' },
        providerId: 'quicknode',
      });
    });

    it('should read a quicknode url without a network segment as ethereum', () => {
      expect(detectRpcProvider('https://hidden-vineyard.quiknode.pro/token123/')).toEqual({
        chain: Blockchain.ETH,
        credentials: { endpointName: 'hidden-vineyard', key: 'token123' },
        providerId: 'quicknode',
      });
    });

    it('should match a provider network rotki does not support, without a chain', () => {
      const match = detectRpcProvider('https://linea-mainnet.g.alchemy.com/v2/key-123');
      expect(match).toMatchObject({ providerId: 'alchemy' });
      expect(match?.chain).toBeUndefined();
    });

    it.each([
      ['an unknown host', 'https://rpc.ankr.com/eth'],
      ['an empty endpoint, as the etherscan node has', ''],
      ['a bare hostname with no key', 'https://mainnet.infura.io'],
      ['an infura url with the wrong path prefix', 'https://mainnet.infura.io/v2/abcdef'],
      ['an infura url with an extra path segment', 'https://mainnet.infura.io/v3/abcdef/extra'],
      ['a nested infura subdomain', 'https://a.b.infura.io/v3/abcdef'],
      ['the provider apex with no subdomain', 'https://infura.io/v3/abcdef'],
      ['a websocket endpoint', 'wss://mainnet.infura.io/ws/v3/abcdef'],
      ['a quicknode url with too many labels', 'https://a.b.c.quiknode.pro/token/'],
      ['garbage', 'not a url'],
    ])('should not detect a provider from %s', (_case, endpoint) => {
      expect(detectRpcProvider(endpoint)).toBeUndefined();
    });

    it('should tolerate surrounding whitespace', () => {
      expect(detectRpcProvider('  https://mainnet.infura.io/v3/abcdef  ')).toMatchObject({
        providerId: 'infura',
      });
    });
  });

  describe('buildRpcEndpoint', () => {
    const infura: RpcProviderMatch = {
      chain: Blockchain.ETH,
      credentials: { key: 'abcdef' },
      providerId: 'infura',
    };

    it('should build every chain the provider serves from one key', () => {
      expect(buildRpcEndpoint(infura, Blockchain.ETH)).toBe('https://mainnet.infura.io/v3/abcdef');
      expect(buildRpcEndpoint(infura, Blockchain.BSC)).toBe('https://bsc-mainnet.infura.io/v3/abcdef');
    });

    it('should return undefined for a chain the provider does not serve', () => {
      expect(buildRpcEndpoint(infura, Blockchain.GNOSIS)).toBeUndefined();
    });

    it('should use the provider\'s own name for a chain, not rotki\'s', () => {
      expect(buildRpcEndpoint(infura, Blockchain.HYPERLIQUID)).toBe('https://hyperevm-mainnet.infura.io/v3/abcdef');
      expect(buildRpcEndpoint({ ...infura, providerId: 'alchemy' }, Blockchain.OPTIMISM))
        .toBe('https://opt-mainnet.g.alchemy.com/v2/abcdef');
    });

    it('should round-trip a detected endpoint back to itself', () => {
      const endpoint = 'https://hidden-vineyard.optimism.quiknode.pro/token123/';
      const match = detectRpcProvider(endpoint);
      expect(match).toBeDefined();
      expect(buildRpcEndpoint(match!, Blockchain.OPTIMISM)).toBe(endpoint);
    });

    it.each([
      [Blockchain.OPTIMISM, 'optimism'],
      [Blockchain.POLYGON_POS, 'matic'],
      [Blockchain.GNOSIS, 'xdai'],
      [Blockchain.BSC, 'bsc'],
      [Blockchain.ARBITRUM_ONE, 'arbitrum-mainnet'],
      [Blockchain.SONIC, 'sonic-mainnet'],
    ])('should address quicknode %s at its own network name', (chain, network) => {
      const match = detectRpcProvider('https://vineyard.optimism.quiknode.pro/token/');
      expect(buildRpcEndpoint(match!, chain)).toBe(`https://vineyard.${network}.quiknode.pro/token/`);
    });

    it('should not offer a quicknode chain whose url needs a path segment', () => {
      const match = detectRpcProvider('https://vineyard.optimism.quiknode.pro/token/');
      expect(buildRpcEndpoint(match!, Blockchain.HYPERLIQUID)).toBeUndefined();
    });

    it('should build quicknode ethereum without a network segment', () => {
      const match = detectRpcProvider('https://hidden-vineyard.optimism.quiknode.pro/token123/');
      expect(buildRpcEndpoint(match!, Blockchain.ETH)).toBe('https://hidden-vineyard.quiknode.pro/token123/');
    });
  });

  describe('getRpcProvider', () => {
    it('should expose the chains a provider serves', () => {
      const provider = getRpcProvider('alchemy');
      expect(provider.name).toBe('Alchemy');
      expect(provider.enablement).toBe('none');
      expect(provider.chains).toContain(Blockchain.GNOSIS);
    });

    it('should keep the three providers\' enablement rules apart', () => {
      expect(getRpcProvider('infura').enablement).toBe('per-network');
      expect(getRpcProvider('quicknode').enablement).toBe('multichain-endpoint');
      expect(getRpcProvider('alchemy').enablement).toBe('none');
    });

    it('should serve every chain it lists', () => {
      for (const id of ['infura', 'alchemy', 'quicknode'] as const) {
        const match: RpcProviderMatch = {
          credentials: { endpointName: 'name', key: 'key' },
          providerId: id,
        };
        for (const chain of getRpcProvider(id).chains)
          expect(buildRpcEndpoint(match, chain)).toBeDefined();
      }
    });
  });

  describe('isRpcProviderEndpoint', () => {
    it('should recognise any url on the provider host', () => {
      expect(isRpcProviderEndpoint('https://polygon-mainnet.infura.io/v3/other', 'infura')).toBe(true);
      expect(isRpcProviderEndpoint('https://polygon-mainnet.infura.io/v3/other', 'alchemy')).toBe(false);
      expect(isRpcProviderEndpoint('', 'infura')).toBe(false);
    });
  });

  describe('maskRpcEndpoint', () => {
    it('should hide the key inside an endpoint', () => {
      expect(maskRpcEndpoint('https://mainnet.infura.io/v3/0123456789abcdef', '0123456789abcdef'))
        .toBe('https://mainnet.infura.io/v3/0123…cdef');
    });

    it('should hide every occurrence, since a backend error quotes the endpoint twice', () => {
      const key = '0123456789abcdef';
      const error = `Failed to connect to node at https://mainnet.infura.io/v3/${key} at endpoint https://mainnet.infura.io/v3/${key}`;

      expect(maskRpcEndpoint(error, key)).not.toContain(key);
    });

    it('should leave a keyless endpoint alone', () => {
      expect(maskRpcEndpoint('https://eth-rpc.publicnode.com', '')).toBe('https://eth-rpc.publicnode.com');
    });
  });

  describe('maskRpcKey', () => {
    it('should keep the ends of a long key and hide the rest', () => {
      expect(maskRpcKey('0123456789abcdef')).toBe('0123…cdef');
    });

    it('should hide a short key entirely', () => {
      expect(maskRpcKey('0123456789')).toBe('…');
    });
  });
});
