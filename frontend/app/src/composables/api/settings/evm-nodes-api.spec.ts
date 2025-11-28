import type { BlockchainRpcNode } from '@/types/settings/rpc';
import { Blockchain } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEvmNodesApi } from '@/composables/api/settings/evm-nodes-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/settings/evm-nodes-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchEvmNodes', () => {
    it('fetches EVM nodes for default ETH chain', async () => {
      const mockNodes: BlockchainRpcNode[] = [
        {
          identifier: 1,
          name: 'Node 1',
          endpoint: 'https://eth.example.com',
          active: true,
          owned: false,
          weight: 50,
          blockchain: 'ETH',
        },
        {
          identifier: 2,
          name: 'Node 2',
          endpoint: 'https://eth2.example.com',
          active: false,
          owned: true,
          weight: 30,
          blockchain: 'ETH',
        },
      ];

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/ETH/nodes`, () =>
          HttpResponse.json({
            result: mockNodes,
            message: '',
          })),
      );

      const { fetchEvmNodes } = useEvmNodesApi();
      const result = await fetchEvmNodes();

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual(mockNodes[0]);
      expect(result[1]).toEqual(mockNodes[1]);
    });

    it('fetches EVM nodes for specified chain', async () => {
      const mockNodes: BlockchainRpcNode[] = [
        {
          identifier: 1,
          name: 'Optimism Node',
          endpoint: 'https://optimism.example.com',
          active: true,
          owned: true,
          weight: 100,
          blockchain: 'OPTIMISM',
        },
      ];

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/OPTIMISM/nodes`, () =>
          HttpResponse.json({
            result: mockNodes,
            message: '',
          })),
      );

      const { fetchEvmNodes } = useEvmNodesApi(ref(Blockchain.OPTIMISM));
      const result = await fetchEvmNodes();

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual(mockNodes[0]);
    });
  });

  describe('addEvmNode', () => {
    it('adds a new EVM node with correct snake_case payload', async () => {
      let requestBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/ETH/nodes`, async ({ request }) => {
          requestBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addEvmNode } = useEvmNodesApi();
      const newNode = {
        name: 'New Node',
        endpoint: 'https://new.example.com',
        active: true,
        owned: true,
        weight: 75,
        blockchain: 'ETH',
      };

      const result = await addEvmNode(newNode);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        name: 'New Node',
        endpoint: 'https://new.example.com',
        active: true,
        owned: true,
        weight: 75,
        blockchain: 'ETH',
      });
    });
  });

  describe('editEvmNode', () => {
    it('edits an existing EVM node with correct snake_case payload', async () => {
      let requestBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/ETH/nodes`, async ({ request }) => {
          requestBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editEvmNode } = useEvmNodesApi();
      const editedNode: BlockchainRpcNode = {
        identifier: 1,
        name: 'Updated Node',
        endpoint: 'https://updated.example.com',
        active: false,
        owned: true,
        weight: 25,
        blockchain: 'ETH',
      };

      const result = await editEvmNode(editedNode);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        identifier: 1,
        name: 'Updated Node',
        endpoint: 'https://updated.example.com',
        active: false,
        owned: true,
        weight: 25,
        blockchain: 'ETH',
      });
    });
  });

  describe('deleteEvmNode', () => {
    it('deletes an EVM node by identifier', async () => {
      let requestBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/ETH/nodes`, async ({ request }) => {
          requestBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteEvmNode } = useEvmNodesApi();
      const result = await deleteEvmNode(42);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        identifier: 42,
      });
    });
  });

  describe('reConnectNode', () => {
    it('reconnects a specific node by identifier', async () => {
      let requestBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/ETH/nodes`, async ({ request }) => {
          requestBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { reConnectNode } = useEvmNodesApi();
      const result = await reConnectNode(5);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        identifier: 5,
      });
    });

    it('reconnects all nodes when no identifier provided', async () => {
      let requestBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/ETH/nodes`, async ({ request }) => {
          requestBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { reConnectNode } = useEvmNodesApi();
      const result = await reConnectNode();

      expect(result).toBe(true);
      expect(requestBody).toEqual({});
    });
  });

  describe('dynamic chain parameter', () => {
    it('uses correct URL when chain ref changes', async () => {
      const chainRef = ref(Blockchain.ETH);
      let requestedUrl = '';

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/polygon_pos/nodes`, ({ request }) => {
          requestedUrl = request.url;
          return HttpResponse.json({
            result: [],
            message: '',
          });
        }),
      );

      const { fetchEvmNodes } = useEvmNodesApi(chainRef);

      chainRef.value = Blockchain.POLYGON_POS;
      await fetchEvmNodes();

      expect(requestedUrl).toContain('/blockchains/polygon_pos/nodes');
    });
  });
});
