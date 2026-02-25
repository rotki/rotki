import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGnosisPaySiweApi } from './use-gnosis-pay-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('useGnosisPaySiweApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchGnosisPayAdmins', () => {
    it('should send GET request and returns admins mapping', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/services/gnosispay/admins`, () =>
          HttpResponse.json({
            result: {
              '0xAdmin1': ['0xSafe1', '0xSafe2'],
              '0xAdmin2': ['0xSafe3'],
            },
            message: '',
          })),
      );

      const { fetchGnosisPayAdmins } = useGnosisPaySiweApi();
      const result = await fetchGnosisPayAdmins();

      expect(result['0xAdmin1']).toEqual(['0xSafe1', '0xSafe2']);
      expect(result['0xAdmin2']).toEqual(['0xSafe3']);
    });

    it('should return empty object when no admins', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/services/gnosispay/admins`, () =>
          HttpResponse.json({
            result: {},
            message: '',
          })),
      );

      const { fetchGnosisPayAdmins } = useGnosisPaySiweApi();
      const result = await fetchGnosisPayAdmins();

      expect(result).toEqual({});
    });
  });

  describe('fetchNonce', () => {
    it('should send GET request with async_query param and returns pending task', async () => {
      let capturedUrl: URL | undefined;

      server.use(
        http.get(`${backendUrl}/api/1/services/gnosispay/nonce`, ({ request }) => {
          capturedUrl = new URL(request.url);
          return HttpResponse.json({
            result: { taskId: 123 },
            message: '',
          });
        }),
      );

      const { fetchNonce } = useGnosisPaySiweApi();
      const result = await fetchNonce();

      expect(capturedUrl).toBeDefined();
      expect(capturedUrl!.searchParams.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });
  });

  describe('verifySiweSignature', () => {
    it('should send POST request with snake_case payload', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/services/gnosispay/token`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { taskId: 456 },
            message: '',
          });
        }),
      );

      const { verifySiweSignature } = useGnosisPaySiweApi();
      const result = await verifySiweSignature(
        'Sign-In with Ethereum message',
        '0xSignature123',
      );

      expect(capturedBody).toEqual({
        async_query: true,
        message: 'Sign-In with Ethereum message',
        signature: '0xSignature123',
      });

      expect(result.taskId).toBe(456);
    });
  });
});
