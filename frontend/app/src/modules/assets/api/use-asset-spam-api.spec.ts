import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetSpamApi } from './use-asset-spam-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('useAssetSpamApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('markAssetsAsSpam', () => {
    it('should send POST request with tokens array', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/assets/spam`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { markAssetsAsSpam } = useAssetSpamApi();
      const result = await markAssetsAsSpam(['0xSpamToken1', '0xSpamToken2']);

      expect(capturedBody).toEqual({
        tokens: ['0xSpamToken1', '0xSpamToken2'],
      });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/spam`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid token address',
          })),
      );

      const { markAssetsAsSpam } = useAssetSpamApi();

      await expect(markAssetsAsSpam(['invalid']))
        .rejects
        .toThrow('Invalid token address');
    });
  });

  describe('removeAssetFromSpamList', () => {
    it('should send DELETE request with token in body', async () => {
      let capturedBody: unknown;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/spam`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { removeAssetFromSpamList } = useAssetSpamApi();
      const result = await removeAssetFromSpamList('0xToken123');

      expect(capturedBody).toEqual({ token: '0xToken123' });
      expect(result).toBe(true);
    });

    it('should throw error when token not found', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/spam`, () =>
          HttpResponse.json({
            result: null,
            message: 'Token not found in spam list',
          })),
      );

      const { removeAssetFromSpamList } = useAssetSpamApi();

      await expect(removeAssetFromSpamList('0xUnknown'))
        .rejects
        .toThrow('Token not found in spam list');
    });
  });
});
