import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetWhitelistApi } from './use-asset-whitelist-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('useAssetWhitelistApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getWhitelistedAssets', () => {
    it('should send GET request and returns asset list', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/ignored/whitelist`, () =>
          HttpResponse.json({
            result: ['ETH', 'BTC', 'USDC'],
            message: '',
          })),
      );

      const { getWhitelistedAssets } = useAssetWhitelistApi();
      const result = await getWhitelistedAssets();

      expect(result).toEqual(['ETH', 'BTC', 'USDC']);
    });

    it('should return empty array when no assets are whitelisted', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/ignored/whitelist`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { getWhitelistedAssets } = useAssetWhitelistApi();
      const result = await getWhitelistedAssets();

      expect(result).toEqual([]);
    });
  });

  describe('addAssetToWhitelist', () => {
    it('should send POST request with token', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/assets/ignored/whitelist`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addAssetToWhitelist } = useAssetWhitelistApi();
      const result = await addAssetToWhitelist('0xNewToken');

      expect(capturedBody).toEqual({ token: '0xNewToken' });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/ignored/whitelist`, () =>
          HttpResponse.json({
            result: null,
            message: 'Token already whitelisted',
          })),
      );

      const { addAssetToWhitelist } = useAssetWhitelistApi();

      await expect(addAssetToWhitelist('0xExisting'))
        .rejects
        .toThrow('Token already whitelisted');
    });
  });

  describe('removeAssetFromWhitelist', () => {
    it('should send DELETE request with token in body', async () => {
      let capturedBody: unknown;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/ignored/whitelist`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { removeAssetFromWhitelist } = useAssetWhitelistApi();
      const result = await removeAssetFromWhitelist('0xToken123');

      expect(capturedBody).toEqual({ token: '0xToken123' });
      expect(result).toBe(true);
    });

    it('should throw error when token not found', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/ignored/whitelist`, () =>
          HttpResponse.json({
            result: null,
            message: 'Token not in whitelist',
          })),
      );

      const { removeAssetFromWhitelist } = useAssetWhitelistApi();

      await expect(removeAssetFromWhitelist('0xUnknown'))
        .rejects
        .toThrow('Token not in whitelist');
    });
  });
});
