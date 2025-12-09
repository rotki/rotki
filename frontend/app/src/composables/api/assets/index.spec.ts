import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/assets/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('checkForAssetUpdate', () => {
    it('checks for asset updates as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/assets/updates`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { checkForAssetUpdate } = useAssetsApi();
      const result = await checkForAssetUpdate();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/updates`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to check for updates',
          })),
      );

      const { checkForAssetUpdate } = useAssetsApi();

      await expect(checkForAssetUpdate())
        .rejects
        .toThrow('Failed to check for updates');
    });
  });

  describe('performUpdate', () => {
    it('performs asset update with version', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/updates`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { performUpdate } = useAssetsApi();
      const result = await performUpdate(15);

      expect(capturedBody).toEqual({
        async_query: true,
        up_to_version: 15,
      });
      expect(result.taskId).toBe(456);
    });

    it('performs update with conflict resolution', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/updates`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 789 },
            message: '',
          });
        }),
      );

      const { performUpdate } = useAssetsApi();
      const conflicts: Readonly<Record<string, 'local' | 'remote'>> = { ETH: 'local', BTC: 'remote' };
      const result = await performUpdate(16, conflicts);

      expect(capturedBody).toEqual({
        async_query: true,
        up_to_version: 16,
        conflicts,
      });
      expect(result.taskId).toBe(789);
    });

    it('preserves asset identifier keys in conflicts without snake_case transformation', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/updates`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 999 },
            message: '',
          });
        }),
      );

      const { performUpdate } = useAssetsApi();
      // Asset identifiers in CAIP format should NOT be transformed to snake_case
      const conflicts: Readonly<Record<string, 'local' | 'remote'>> = {
        'eip155:1/erc20:0x6B175474E89094C44Da98b954EesdicdDAD': 'local',
        'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 'remote',
        'solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp/spl:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'local',
      };
      const result = await performUpdate(17, conflicts);

      // Verify the payload keys are NOT transformed to snake_case
      // Before the fix, 'eip155:1/erc20:0x...' would be incorrectly transformed
      expect(capturedBody).toEqual({
        async_query: true,
        up_to_version: 17,
        conflicts,
      });
      expect(result.taskId).toBe(999);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/updates`, () =>
          HttpResponse.json({
            result: null,
            message: 'Update failed',
          })),
      );

      const { performUpdate } = useAssetsApi();

      await expect(performUpdate(15))
        .rejects
        .toThrow('Update failed');
    });
  });

  describe('mergeAssets', () => {
    it('merges two assets successfully', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/replace`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { mergeAssets } = useAssetsApi();
      const result = await mergeAssets('OLD_TOKEN', 'NEW_TOKEN');

      expect(capturedBody).toEqual({
        source_identifier: 'OLD_TOKEN',
        target_asset: 'NEW_TOKEN',
      });
      expect(result).toBe(true);
    });

    it('throws error on merge failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/replace`, () =>
          HttpResponse.json({
            result: null,
            message: 'Cannot merge assets',
          })),
      );

      const { mergeAssets } = useAssetsApi();

      await expect(mergeAssets('OLD', 'NEW'))
        .rejects
        .toThrow('Cannot merge assets');
    });
  });

  describe('restoreAssetsDatabase', () => {
    it('restores database with soft reset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/updates`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 101 },
            message: '',
          });
        }),
      );

      const { restoreAssetsDatabase } = useAssetsApi();
      const result = await restoreAssetsDatabase('soft', false);

      expect(capturedBody).toEqual({
        async_query: true,
        ignore_warnings: false,
        reset: 'soft',
      });
      expect(result.taskId).toBe(101);
    });

    it('restores database with hard reset and ignore warnings', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/updates`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 102 },
            message: '',
          });
        }),
      );

      const { restoreAssetsDatabase } = useAssetsApi();
      const result = await restoreAssetsDatabase('hard', true);

      expect(capturedBody).toEqual({
        async_query: true,
        ignore_warnings: true,
        reset: 'hard',
      });
      expect(result.taskId).toBe(102);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/updates`, () =>
          HttpResponse.json({
            result: null,
            message: 'Restore failed',
          })),
      );

      const { restoreAssetsDatabase } = useAssetsApi();

      await expect(restoreAssetsDatabase('soft', false))
        .rejects
        .toThrow('Restore failed');
    });
  });

  describe('importCustom', () => {
    it('imports custom assets from file upload', async () => {
      let capturedFormData: FormData | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/user`, async ({ request }) => {
          capturedFormData = await request.formData();
          return HttpResponse.json({
            result: { task_id: 201 },
            message: '',
          });
        }),
      );

      const { importCustom } = useAssetsApi();
      const file = new File(['test'], 'assets.json', { type: 'application/json' });
      const result = await importCustom(file);

      expect(capturedFormData!.get('async_query')).toBe('true');
      expect(capturedFormData!.get('file')).toBeInstanceOf(File);
      expect(result.taskId).toBe(201);
    });

    it('imports custom assets from file path', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/user`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 202 },
            message: '',
          });
        }),
      );

      const { importCustom } = useAssetsApi();
      const result = await importCustom('/path/to/assets.json');

      expect(capturedBody).toEqual({
        action: 'upload',
        async_query: true,
        file: '/path/to/assets.json',
      });
      expect(result.taskId).toBe(202);
    });

    it('throws error on import failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/user`, () =>
          HttpResponse.json({
            result: null,
            message: 'Import failed',
          })),
      );

      const { importCustom } = useAssetsApi();
      const file = new File(['test'], 'assets.json');

      await expect(importCustom(file))
        .rejects
        .toThrow('Import failed');
    });
  });

  describe('exportCustom', () => {
    it('exports as blob download when no directory provided', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/user`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return new HttpResponse('test file content', {
            status: 200,
            headers: {
              'Content-Type': 'application/octet-stream',
            },
          });
        }),
      );

      const { exportCustom } = useAssetsApi();
      const result = await exportCustom();

      expect(capturedBody).toEqual({
        action: 'download',
      });
      expect(result.success).toBe(true);
    });

    it('exports to directory path', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/user`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { file: '/export/assets.zip' },
            message: '',
          });
        }),
      );

      const { exportCustom } = useAssetsApi();
      const result = await exportCustom('/export/dir');

      expect(capturedBody).toEqual({
        action: 'download',
        destination: '/export/dir',
      });
      expect(result.success).toBe(true);
    });

    it('returns error status on directory export failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/user`, () =>
          HttpResponse.json({
            result: null,
            message: 'Export failed',
          })),
      );

      const { exportCustom } = useAssetsApi();
      const result = await exportCustom('/export/dir');

      expect(result.success).toBe(false);
      if (!result.success)
        expect(result.message).toBe('Export failed');
    });

    it('returns error status on blob export failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/user`, () =>
          HttpResponse.json({
            result: null,
            message: 'Blob export failed',
          })),
      );

      const { exportCustom } = useAssetsApi();
      const result = await exportCustom();

      expect(result.success).toBe(false);
      if (!result.success)
        expect(result.message).toBe('Blob export failed');
    });
  });

  describe('fetchNfts', () => {
    it('fetches NFTs without ignoring cache', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/nfts`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: { task_id: 301 },
            message: '',
          });
        }),
      );

      const { fetchNfts } = useAssetsApi();
      const result = await fetchNfts(false);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.has('ignore_cache')).toBe(false);
      expect(result.taskId).toBe(301);
    });

    it('fetches NFTs with ignore cache', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/nfts`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: { task_id: 302 },
            message: '',
          });
        }),
      );

      const { fetchNfts } = useAssetsApi();
      const result = await fetchNfts(true);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('ignore_cache')).toBe('true');
      expect(result.taskId).toBe(302);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/nfts`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch NFTs',
          })),
      );

      const { fetchNfts } = useAssetsApi();

      await expect(fetchNfts(false))
        .rejects
        .toThrow('Failed to fetch NFTs');
    });
  });
});
