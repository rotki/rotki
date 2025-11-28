import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSupportedChainsApi } from './chains';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/info/chains', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchSupportedChains', () => {
    it('fetches supported chains and parses response', async () => {
      const mockChains = [
        {
          id: 'ETH',
          name: 'ethereum',
          type: 'evm',
          image: 'ethereum.svg',
          evm_chain_name: 'ethereum',
          native_token: 'ETH',
        },
        {
          id: 'BTC',
          name: 'bitcoin',
          type: 'btclike',
          image: 'bitcoin.svg',
        },
        {
          id: 'KSM',
          name: 'kusama',
          type: 'substrate',
          image: 'kusama.svg',
          native_token: 'KSM',
        },
      ];

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/supported`, () =>
          HttpResponse.json({
            result: mockChains,
            message: '',
          })),
      );

      const { fetchSupportedChains } = useSupportedChainsApi();
      const result = await fetchSupportedChains();

      expect(result).toHaveLength(3);
      expect(result[0].id).toBe('ETH');
      expect(result[0].name).toBe('Ethereum');
      expect(result[0].type).toBe('evm');
      expect(result[1].id).toBe('BTC');
      expect(result[1].name).toBe('Bitcoin');
      expect(result[2].id).toBe('KSM');
      expect(result[2].name).toBe('Kusama');
      expect(result[2].type).toBe('substrate');
    });

    it('returns empty array when no chains', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/supported`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { fetchSupportedChains } = useSupportedChainsApi();
      const result = await fetchSupportedChains();

      expect(result).toEqual([]);
    });

    it('handles evmlike chain type', async () => {
      const mockChains = [
        {
          id: 'ZKSYNC_LITE',
          name: 'zksync lite',
          type: 'evmlike',
          image: 'zksync.svg',
          native_token: 'ETH',
        },
      ];

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/supported`, () =>
          HttpResponse.json({
            result: mockChains,
            message: '',
          })),
      );

      const { fetchSupportedChains } = useSupportedChainsApi();
      const result = await fetchSupportedChains();

      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('ZKSYNC_LITE');
      expect(result[0].name).toBe('Zksync Lite');
      expect(result[0].type).toBe('evmlike');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/supported`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch supported chains',
          })),
      );

      const { fetchSupportedChains } = useSupportedChainsApi();

      await expect(fetchSupportedChains())
        .rejects
        .toThrow('Failed to fetch supported chains');
    });
  });

  describe('fetchAllEvmChains', () => {
    it('fetches all EVM chains and parses response', async () => {
      const mockEvmChains = [
        { id: 1, name: 'ethereum', label: 'Ethereum Mainnet' },
        { id: 10, name: 'optimism', label: 'Optimism' },
        { id: 137, name: 'polygon_pos', label: 'Polygon PoS' },
        { id: 42161, name: 'arbitrum_one', label: 'Arbitrum One' },
      ];

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/evm/all`, () =>
          HttpResponse.json({
            result: mockEvmChains,
            message: '',
          })),
      );

      const { fetchAllEvmChains } = useSupportedChainsApi();
      const result = await fetchAllEvmChains();

      expect(result).toHaveLength(4);
      expect(result[0]).toEqual({ id: 1, name: 'ethereum', label: 'Ethereum Mainnet' });
      expect(result[1]).toEqual({ id: 10, name: 'optimism', label: 'Optimism' });
      expect(result[2]).toEqual({ id: 137, name: 'polygon_pos', label: 'Polygon PoS' });
      expect(result[3]).toEqual({ id: 42161, name: 'arbitrum_one', label: 'Arbitrum One' });
    });

    it('returns empty array when no EVM chains', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/evm/all`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { fetchAllEvmChains } = useSupportedChainsApi();
      const result = await fetchAllEvmChains();

      expect(result).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/evm/all`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch EVM chains',
          })),
      );

      const { fetchAllEvmChains } = useSupportedChainsApi();

      await expect(fetchAllEvmChains())
        .rejects
        .toThrow('Failed to fetch EVM chains');
    });
  });
});
