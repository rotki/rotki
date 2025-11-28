import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetIconApi } from './icon';

const backendUrl = process.env.VITE_BACKEND_URL;
const colibriUrl = process.env.VITE_COLIBRI_URL;

describe('composables/api/assets/icon', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('assetImageUrl', () => {
    it('returns icon URL for identifier', () => {
      const { assetImageUrl } = useAssetIconApi();
      const url = assetImageUrl('ETH');

      expect(url).toContain('/assets/icon?asset_id=ETH');
    });

    it('encodes identifier with special characters', () => {
      const { assetImageUrl } = useAssetIconApi();
      const url = assetImageUrl('eip155:1/erc20:0x1234');

      expect(url).toContain('asset_id=eip155%3A1%2Ferc20%3A0x1234');
    });

    it('appends random string when provided', () => {
      const { assetImageUrl } = useAssetIconApi();
      const url = assetImageUrl('ETH', '12345');

      expect(url).toContain('asset_id=ETH');
      expect(url).toContain('&t=12345');
    });

    it('appends numeric random value', () => {
      const { assetImageUrl } = useAssetIconApi();
      const url = assetImageUrl('BTC', 67890);

      expect(url).toContain('&t=67890');
    });
  });

  describe('checkAsset', () => {
    it('returns 200 for existing asset', async () => {
      server.use(
        http.head(`${colibriUrl}/assets/icon`, () =>
          new HttpResponse(null, { status: 200 })),
      );

      const { checkAsset } = useAssetIconApi();
      const status = await checkAsset('ETH', {});

      expect(status).toBe(200);
    });

    it('returns 404 for non-existing asset', async () => {
      server.use(
        http.head(`${colibriUrl}/assets/icon`, () =>
          new HttpResponse(null, { status: 404 })),
      );

      const { checkAsset } = useAssetIconApi();
      const status = await checkAsset('UNKNOWN', {});

      expect(status).toBe(404);
    });

    it('returns 202 for pending asset', async () => {
      server.use(
        http.head(`${colibriUrl}/assets/icon`, () =>
          new HttpResponse(null, { status: 202 })),
      );

      const { checkAsset } = useAssetIconApi();
      const status = await checkAsset('PENDING', {});

      expect(status).toBe(202);
    });
  });

  describe('uploadIcon', () => {
    it('uploads icon file successfully', async () => {
      let capturedFormData: FormData | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/icon/modify`, async ({ request }) => {
          capturedFormData = await request.formData();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { uploadIcon } = useAssetIconApi();
      const file = new File(['test'], 'icon.png', { type: 'image/png' });
      const result = await uploadIcon('ETH', file);

      expect(capturedFormData!.get('asset')).toBe('ETH');
      expect(capturedFormData!.get('file')).toBeInstanceOf(File);
      expect(result).toBe(true);
    });

    it('throws error on upload failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/icon/modify`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to upload icon',
          })),
      );

      const { uploadIcon } = useAssetIconApi();
      const file = new File(['test'], 'icon.png', { type: 'image/png' });

      await expect(uploadIcon('ETH', file))
        .rejects
        .toThrow('Failed to upload icon');
    });
  });

  describe('setIcon', () => {
    it('sets icon from file path', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/icon/modify`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { setIcon } = useAssetIconApi();
      const result = await setIcon('ETH', '/path/to/icon.png');

      expect(capturedBody).toEqual({
        asset: 'ETH',
        file: '/path/to/icon.png',
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/icon/modify`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to set icon',
          })),
      );

      const { setIcon } = useAssetIconApi();

      await expect(setIcon('ETH', '/invalid/path'))
        .rejects
        .toThrow('Failed to set icon');
    });
  });

  describe('refreshIcon', () => {
    it('refreshes icon for asset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/assets/icon/modify`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { refreshIcon } = useAssetIconApi();
      const result = await refreshIcon('ETH');

      expect(capturedBody).toEqual({ asset: 'ETH' });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/assets/icon/modify`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to refresh icon',
          })),
      );

      const { refreshIcon } = useAssetIconApi();

      await expect(refreshIcon('ETH'))
        .rejects
        .toThrow('Failed to refresh icon');
    });
  });

  describe('clearIconCache', () => {
    it('clears cache for specific assets', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/cache/icons/clear`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { clearIconCache } = useAssetIconApi();
      const result = await clearIconCache(['ETH', 'BTC']);

      expect(capturedBody).toEqual({ entries: ['ETH', 'BTC'] });
      expect(result).toBe(true);
    });

    it('clears all cache when assets is null', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/cache/icons/clear`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { clearIconCache } = useAssetIconApi();
      const result = await clearIconCache(null);

      expect(capturedBody).toEqual({ entries: null });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/cache/icons/clear`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to clear cache',
          })),
      );

      const { clearIconCache } = useAssetIconApi();

      await expect(clearIconCache(['ETH']))
        .rejects
        .toThrow('Failed to clear cache');
    });
  });
});
