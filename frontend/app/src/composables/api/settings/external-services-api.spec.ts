import type { ExternalServiceKey } from '@/types/user';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExternalServicesApi } from './external-services-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/settings/external-services-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryExternalServices', () => {
    it('queries external services', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/external_services`, () =>
          HttpResponse.json({
            result: {
              etherscan: { api_key: 'etherscan-key-123' },
              coingecko: { api_key: 'coingecko-key-456' },
            },
            message: '',
          })),
      );

      const { queryExternalServices } = useExternalServicesApi();
      const result = await queryExternalServices();

      expect(result.etherscan?.apiKey).toBe('etherscan-key-123');
      expect(result.coingecko?.apiKey).toBe('coingecko-key-456');
    });

    it('returns empty object when no services configured', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/external_services`, () =>
          HttpResponse.json({
            result: {},
            message: '',
          })),
      );

      const { queryExternalServices } = useExternalServicesApi();
      const result = await queryExternalServices();

      expect(result.etherscan).toBeUndefined();
      expect(result.coingecko).toBeUndefined();
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/external_services`, () =>
          HttpResponse.json({
            result: null,
            message: 'Service unavailable',
          })),
      );

      const { queryExternalServices } = useExternalServicesApi();

      await expect(queryExternalServices())
        .rejects
        .toThrow('Service unavailable');
    });
  });

  describe('setExternalServices', () => {
    it('sets external services', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/external_services`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              etherscan: { api_key: 'new-etherscan-key' },
            },
            message: '',
          });
        }),
      );

      const { setExternalServices } = useExternalServicesApi();
      const keys: ExternalServiceKey[] = [
        { name: 'etherscan', apiKey: 'new-etherscan-key' },
      ];
      const result = await setExternalServices(keys);

      expect(capturedBody).toEqual({
        services: [{ name: 'etherscan', api_key: 'new-etherscan-key' }],
      });
      expect(result.etherscan?.apiKey).toBe('new-etherscan-key');
    });

    it('sets multiple external services', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/external_services`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              etherscan: { api_key: 'etherscan-key' },
              coingecko: { api_key: 'coingecko-key' },
            },
            message: '',
          });
        }),
      );

      const { setExternalServices } = useExternalServicesApi();
      const keys: ExternalServiceKey[] = [
        { name: 'etherscan', apiKey: 'etherscan-key' },
        { name: 'coingecko', apiKey: 'coingecko-key' },
      ];
      const result = await setExternalServices(keys);

      expect(capturedBody).toEqual({
        services: [
          { name: 'etherscan', api_key: 'etherscan-key' },
          { name: 'coingecko', api_key: 'coingecko-key' },
        ],
      });
      expect(result.etherscan?.apiKey).toBe('etherscan-key');
      expect(result.coingecko?.apiKey).toBe('coingecko-key');
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/external_services`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid API key',
          })),
      );

      const { setExternalServices } = useExternalServicesApi();

      await expect(setExternalServices([]))
        .rejects
        .toThrow('Invalid API key');
    });
  });

  describe('deleteExternalServices', () => {
    it('deletes an external service', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/external_services`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              coingecko: { api_key: 'coingecko-key' },
            },
            message: '',
          });
        }),
      );

      const { deleteExternalServices } = useExternalServicesApi();
      const result = await deleteExternalServices('etherscan');

      expect(capturedBody).toEqual({
        services: ['etherscan'],
      });
      expect(result.etherscan).toBeUndefined();
      expect(result.coingecko?.apiKey).toBe('coingecko-key');
    });

    it('returns empty when last service deleted', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/external_services`, () =>
          HttpResponse.json({
            result: {},
            message: '',
          })),
      );

      const { deleteExternalServices } = useExternalServicesApi();
      const result = await deleteExternalServices('etherscan');

      expect(result).toEqual({});
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/external_services`, () =>
          HttpResponse.json({
            result: null,
            message: 'Service not found',
          })),
      );

      const { deleteExternalServices } = useExternalServicesApi();

      await expect(deleteExternalServices('unknown'))
        .rejects
        .toThrow('Service not found');
    });
  });
});
