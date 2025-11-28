import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetManagementApi } from './management';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/assets/management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryAllAssets', () => {
    it('queries all assets with pagination', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/all`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [
                {
                  identifier: 'ETH',
                  name: 'Ethereum',
                  symbol: 'ETH',
                  asset_type: 'own chain',
                },
                {
                  identifier: 'BTC',
                  name: 'Bitcoin',
                  symbol: 'BTC',
                  asset_type: 'own chain',
                },
              ],
              entries_found: 2,
              entries_limit: 100,
              entries_total: 50,
            },
            message: '',
          });
        }),
      );

      const { queryAllAssets } = useAssetManagementApi();
      const result = await queryAllAssets({
        limit: 100,
        offset: 0,
        orderByAttributes: ['name'],
        ascending: [true],
      });

      expect(capturedBody).toEqual({
        limit: 100,
        offset: 0,
        order_by_attributes: ['name'],
        ascending: [true],
      });
      expect(result.data).toHaveLength(2);
      expect(result.found).toBe(2);
      expect(result.total).toBe(50);
    });

    it('converts solana chain to asset type', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/all`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 100,
              entries_total: 0,
            },
            message: '',
          });
        }),
      );

      const { queryAllAssets } = useAssetManagementApi();
      await queryAllAssets({
        limit: 100,
        offset: 0,
        evmChain: 'solana',
      });

      expect(capturedBody).not.toHaveProperty('evm_chain');
      expect(capturedBody).toHaveProperty('asset_type', 'solana token');
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/all`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to query assets',
          })),
      );

      const { queryAllAssets } = useAssetManagementApi();

      await expect(queryAllAssets({ limit: 100, offset: 0 }))
        .rejects
        .toThrow('Failed to query assets');
    });
  });

  describe('queryAllCustomAssets', () => {
    it('queries custom assets', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/custom`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [
                {
                  identifier: 'custom-1',
                  name: 'Custom Asset',
                  custom_asset_type: 'stocks',
                  notes: null,
                },
              ],
              entries_found: 1,
              entries_limit: 50,
              entries_total: 10,
            },
            message: '',
          });
        }),
      );

      const { queryAllCustomAssets } = useAssetManagementApi();
      const result = await queryAllCustomAssets({
        limit: 50,
        offset: 0,
      });

      expect(capturedBody).toEqual({
        limit: 50,
        offset: 0,
      });
      expect(result.data).toHaveLength(1);
      expect(result.data[0].name).toBe('Custom Asset');
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/custom`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to query custom assets',
          })),
      );

      const { queryAllCustomAssets } = useAssetManagementApi();

      await expect(queryAllCustomAssets({ limit: 50, offset: 0 }))
        .rejects
        .toThrow('Failed to query custom assets');
    });
  });

  describe('queryOwnedAssets', () => {
    it('returns list of owned asset identifiers', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets`, () =>
          HttpResponse.json({
            result: ['ETH', 'BTC', 'USDT'],
            message: '',
          })),
      );

      const { queryOwnedAssets } = useAssetManagementApi();
      const result = await queryOwnedAssets();

      expect(result).toEqual(['ETH', 'BTC', 'USDT']);
    });

    it('handles empty owned assets', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { queryOwnedAssets } = useAssetManagementApi();
      const result = await queryOwnedAssets();

      expect(result).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to query owned assets',
          })),
      );

      const { queryOwnedAssets } = useAssetManagementApi();

      await expect(queryOwnedAssets())
        .rejects
        .toThrow('Failed to query owned assets');
    });
  });

  describe('getAssetTypes', () => {
    it('returns list of asset types', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/types`, () =>
          HttpResponse.json({
            result: ['own chain', 'evm token', 'fiat'],
            message: '',
          })),
      );

      const { getAssetTypes } = useAssetManagementApi();
      const result = await getAssetTypes();

      expect(result).toEqual(['own chain', 'evm token', 'fiat']);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/types`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to get asset types',
          })),
      );

      const { getAssetTypes } = useAssetManagementApi();

      await expect(getAssetTypes())
        .rejects
        .toThrow('Failed to get asset types');
    });
  });

  describe('addAsset', () => {
    it('adds new asset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/all`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { identifier: 'NEW_TOKEN' },
            message: '',
          });
        }),
      );

      const { addAsset } = useAssetManagementApi();
      const result = await addAsset({
        name: 'New Token',
        symbol: 'NEW',
        assetType: 'evm token',
      });

      expect(capturedBody).toEqual({
        name: 'New Token',
        symbol: 'NEW',
        asset_type: 'evm token',
      });
      expect(result.identifier).toBe('NEW_TOKEN');
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/all`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to add asset',
          })),
      );

      const { addAsset } = useAssetManagementApi();

      await expect(addAsset({ name: 'Test', symbol: 'TEST', assetType: 'fiat' }))
        .rejects
        .toThrow('Failed to add asset');
    });
  });

  describe('editAsset', () => {
    it('edits existing asset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/assets/all`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editAsset } = useAssetManagementApi();
      const result = await editAsset({
        identifier: 'TOKEN_1',
        name: 'Updated Token',
        symbol: 'UPD',
        assetType: 'evm token',
      });

      expect(capturedBody).toEqual({
        identifier: 'TOKEN_1',
        name: 'Updated Token',
        symbol: 'UPD',
        asset_type: 'evm token',
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/assets/all`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to edit asset',
          })),
      );

      const { editAsset } = useAssetManagementApi();

      await expect(editAsset({ identifier: 'X', name: 'X', symbol: 'X', assetType: 'fiat' }))
        .rejects
        .toThrow('Failed to edit asset');
    });
  });

  describe('deleteAsset', () => {
    it('deletes asset by identifier', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/all`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteAsset } = useAssetManagementApi();
      const result = await deleteAsset('TOKEN_TO_DELETE');

      expect(capturedBody).toEqual({ identifier: 'TOKEN_TO_DELETE' });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/all`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete asset',
          })),
      );

      const { deleteAsset } = useAssetManagementApi();

      await expect(deleteAsset('X'))
        .rejects
        .toThrow('Failed to delete asset');
    });
  });

  describe('getCustomAssetTypes', () => {
    it('returns list of custom asset types', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/custom/types`, () =>
          HttpResponse.json({
            result: ['stocks', 'bonds', 'real estate'],
            message: '',
          })),
      );

      const { getCustomAssetTypes } = useAssetManagementApi();
      const result = await getCustomAssetTypes();

      expect(result).toEqual(['stocks', 'bonds', 'real estate']);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/custom/types`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to get custom asset types',
          })),
      );

      const { getCustomAssetTypes } = useAssetManagementApi();

      await expect(getCustomAssetTypes())
        .rejects
        .toThrow('Failed to get custom asset types');
    });
  });

  describe('addCustomAsset', () => {
    it('adds new custom asset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/custom`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: 'custom-new-id',
            message: '',
          });
        }),
      );

      const { addCustomAsset } = useAssetManagementApi();
      const result = await addCustomAsset({
        name: 'My Stock',
        customAssetType: 'stocks',
        notes: null,
      });

      expect(capturedBody).toEqual({
        name: 'My Stock',
        custom_asset_type: 'stocks',
        notes: null,
      });
      expect(result).toBe('custom-new-id');
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/custom`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to add custom asset',
          })),
      );

      const { addCustomAsset } = useAssetManagementApi();

      await expect(addCustomAsset({ name: 'Test', customAssetType: 'stocks', notes: null }))
        .rejects
        .toThrow('Failed to add custom asset');
    });
  });

  describe('editCustomAsset', () => {
    it('edits custom asset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/assets/custom`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editCustomAsset } = useAssetManagementApi();
      const result = await editCustomAsset({
        identifier: 'custom-1',
        name: 'Updated Stock',
        customAssetType: 'stocks',
        notes: null,
      });

      expect(capturedBody).toEqual({
        identifier: 'custom-1',
        name: 'Updated Stock',
        custom_asset_type: 'stocks',
        notes: null,
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/assets/custom`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to edit custom asset',
          })),
      );

      const { editCustomAsset } = useAssetManagementApi();

      await expect(editCustomAsset({ identifier: 'x', name: 'x', customAssetType: 'x', notes: null }))
        .rejects
        .toThrow('Failed to edit custom asset');
    });
  });

  describe('deleteCustomAsset', () => {
    it('deletes custom asset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/custom`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteCustomAsset } = useAssetManagementApi();
      const result = await deleteCustomAsset('custom-to-delete');

      expect(capturedBody).toEqual({ identifier: 'custom-to-delete' });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/custom`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete custom asset',
          })),
      );

      const { deleteCustomAsset } = useAssetManagementApi();

      await expect(deleteCustomAsset('x'))
        .rejects
        .toThrow('Failed to delete custom asset');
    });
  });
});
