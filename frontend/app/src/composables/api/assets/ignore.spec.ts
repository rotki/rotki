import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetIgnoreApi } from './ignore';

const backendUrl = process.env.VITE_BACKEND_URL;
const colibriUrl = process.env.VITE_COLIBRI_URL;

describe('composables/api/assets/ignore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useAssetIgnoreApi', () => {
    describe('getIgnoredAssets', () => {
      it('sends GET request to colibri and returns asset list', async () => {
        // Note: getIgnoredAssets overrides baseURL to colibriApiUrl, so URL is without /api/1
        server.use(
          http.get(`${colibriUrl}/assets/ignored`, () =>
            HttpResponse.json({
              result: ['ETH', 'BTC', 'USDT'],
              message: '',
            })),
        );

        const { getIgnoredAssets } = useAssetIgnoreApi();
        const result = await getIgnoredAssets();

        expect(result).toEqual(['ETH', 'BTC', 'USDT']);
      });

      it('returns empty array when no assets are ignored', async () => {
        server.use(
          http.get(`${colibriUrl}/assets/ignored`, () =>
            HttpResponse.json({
              result: [],
              message: '',
            })),
        );

        const { getIgnoredAssets } = useAssetIgnoreApi();
        const result = await getIgnoredAssets();

        expect(result).toEqual([]);
      });
    });

    describe('addIgnoredAssets', () => {
      it('sends PUT request with assets array', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/assets/ignored`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                successful: ['ETH', 'BTC'],
                no_action: [],
              },
              message: '',
            });
          }),
        );

        const { addIgnoredAssets } = useAssetIgnoreApi();
        const result = await addIgnoredAssets(['ETH', 'BTC']);

        expect(capturedBody).toEqual({ assets: ['ETH', 'BTC'] });
        expect(result.successful).toEqual(['ETH', 'BTC']);
        expect(result.noAction).toEqual([]);
      });

      it('returns noAction for already ignored assets', async () => {
        server.use(
          http.put(`${backendUrl}/api/1/assets/ignored`, () =>
            HttpResponse.json({
              result: {
                successful: ['BTC'],
                no_action: ['ETH'],
              },
              message: '',
            })),
        );

        const { addIgnoredAssets } = useAssetIgnoreApi();
        const result = await addIgnoredAssets(['ETH', 'BTC']);

        expect(result.successful).toEqual(['BTC']);
        expect(result.noAction).toEqual(['ETH']);
      });
    });

    describe('removeIgnoredAssets', () => {
      it('sends DELETE request with assets array in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/assets/ignored`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                successful: ['ETH'],
                no_action: [],
              },
              message: '',
            });
          }),
        );

        const { removeIgnoredAssets } = useAssetIgnoreApi();
        const result = await removeIgnoredAssets(['ETH']);

        expect(capturedBody).toEqual({ assets: ['ETH'] });
        expect(result.successful).toEqual(['ETH']);
      });

      it('returns noAction for assets not in ignored list', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/assets/ignored`, () =>
            HttpResponse.json({
              result: {
                successful: [],
                no_action: ['UNKNOWN'],
              },
              message: '',
            })),
        );

        const { removeIgnoredAssets } = useAssetIgnoreApi();
        const result = await removeIgnoredAssets(['UNKNOWN']);

        expect(result.successful).toEqual([]);
        expect(result.noAction).toEqual(['UNKNOWN']);
      });
    });
  });
});
